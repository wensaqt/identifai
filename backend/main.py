import json
import logging
from datetime import datetime, timezone

from classifier import classify_document
from consts.anomalies import AnomalyType, Severity
from consts.process import ProcessStatus, ProcessType
from consts.process_definitions import PROCESS_DEFINITIONS
from db import ProcessRepository
from extractor import extract_fields
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from ocr import extract_text
from process import ProcessAnomaly
from process_runner import ProcessRunner
from validator import validate_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="IdentifAI API")

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB

_repo = ProcessRepository()
_runner = ProcessRunner(repo=_repo)


def _validate_upload(file: UploadFile, file_bytes: bytes) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file type: {file.content_type}"
        )
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB limit")


def _process_document(file_bytes: bytes, filename: str) -> dict:
    result = extract_text(file_bytes, filename)
    result["doc_type"] = classify_document(result["text"])
    result["fields"] = extract_fields(result["text"], result["doc_type"])
    result["validation"] = validate_document(result["doc_type"], result["fields"])
    return result


def _build_expected_map(files: list[UploadFile], doc_types_json: str | None) -> dict[str, str]:
    """Build {filename: expected_doc_type} from the parallel doc_types JSON array."""
    if not doc_types_json:
        return {}
    try:
        types_list = json.loads(doc_types_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {files[i].filename: types_list[i] for i in range(min(len(files), len(types_list)))}


def _detect_type_mismatches(
    classified: list[tuple], expected_map: dict[str, str]
) -> list[ProcessAnomaly]:
    """Return DOC_TYPE_MISMATCH anomalies for files where declared type != classified type."""
    anomalies = []
    for result, _ in classified:
        filename = result.get("filename", "")
        declared = expected_map.get(filename)
        detected = result.get("doc_type")
        if declared and detected and declared != detected:
            anomalies.append(
                ProcessAnomaly(
                    type=AnomalyType.DOC_TYPE_MISMATCH,
                    severity=Severity.WARNING,
                    message=f"Type déclaré '{declared}' ≠ type détecté '{detected}'",
                    document_refs=[filename],
                )
            )
    return anomalies


def _inject_anomalies(process, anomalies: list[ProcessAnomaly]) -> None:
    """Append anomalies to process, recompute status, persist."""
    if not anomalies:
        return
    process.anomalies.extend(anomalies)
    has_error = any(a.severity == Severity.ERROR for a in process.anomalies)
    process.status = ProcessStatus.ERROR if has_error else ProcessStatus.VALID
    _repo.update(process)


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Process CRUD ─────────────────────────────────────────────────────────────


@app.post("/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    doc_types: str = Form(None),
):
    """Full pipeline: OCR + classify + extract + validate + verify → Process."""
    definition = PROCESS_DEFINITIONS[ProcessType.SUPPLIER_COMPLIANCE]
    expected_map = _build_expected_map(files, doc_types)

    # Phase 1 : OCR + classify pour vérifier la complétude
    classified = []
    for file in files:
        file_bytes = await file.read()
        _validate_upload(file, file_bytes)
        result = extract_text(file_bytes, file.filename)
        result["doc_type"] = classify_document(result["text"])
        classified.append((result, file_bytes))

    provided = {r["doc_type"] for r, _ in classified}
    missing = sorted(definition.required_doc_types - provided)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_documents",
                "missing": missing,
                "message": f"Documents manquants : {', '.join(missing)}",
            },
        )

    # Phase 2 : extraction + validation + vérification
    documents = []
    for result, _ in classified:
        result["fields"] = extract_fields(result["text"], result["doc_type"])
        result["validation"] = validate_document(result["doc_type"], result["fields"])
        documents.append(result)

    process = _runner.run(documents, definition)
    _inject_anomalies(process, _detect_type_mismatches(classified, expected_map))
    return process.to_dict()


@app.get("/processes/{process_id}")
def get_process(process_id: str):
    """Retrieve a process by ID."""
    process = _repo.find_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return process.to_dict()


@app.get("/processes")
def list_processes():
    """List all active (non-deleted) processes."""
    return [p.to_dict() for p in _repo.find_active()]


@app.put("/processes/{process_id}")
async def update_process(
    process_id: str,
    files: list[UploadFile] = File(...),
    doc_types: str = Form(None),
):
    """Re-run the pipeline on an existing process with new documents."""
    process = _repo.find_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    if process.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Cannot update a cancelled process")

    definition = PROCESS_DEFINITIONS[ProcessType(process.type)]
    expected_map = _build_expected_map(files, doc_types)

    classified = []
    for file in files:
        file_bytes = await file.read()
        _validate_upload(file, file_bytes)
        result = extract_text(file_bytes, file.filename)
        result["doc_type"] = classify_document(result["text"])
        classified.append((result, file_bytes))

    provided = {r["doc_type"] for r, _ in classified}
    missing = sorted(definition.required_doc_types - provided)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_documents",
                "missing": missing,
                "message": f"Documents manquants : {', '.join(missing)}",
            },
        )

    documents = []
    for result, _ in classified:
        result["fields"] = extract_fields(result["text"], result["doc_type"])
        result["validation"] = validate_document(result["doc_type"], result["fields"])
        documents.append(result)

    updated = _runner.rerun(process, documents, definition)
    _inject_anomalies(updated, _detect_type_mismatches(classified, expected_map))
    return updated.to_dict()


@app.delete("/processes/{process_id}")
def cancel_process(process_id: str):
    """Soft-delete (cancel) a process."""
    process = _repo.find_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    if process.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Process already cancelled")

    deleted_at = datetime.now(tz=timezone.utc).isoformat()
    _repo.soft_delete(process_id, deleted_at)
    process.status = ProcessStatus.CANCELLED
    process.deleted_at = deleted_at
    return process.to_dict()


# ── Single-file & verify ─────────────────────────────────────────────────────


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Single file: OCR + classify + extract + validate."""
    file_bytes = await file.read()
    _validate_upload(file, file_bytes)
    return _process_document(file_bytes, file.filename)


@app.post("/verify")
async def verify(documents: list[dict]):
    """Cross-document verification on pre-processed results → Process."""
    definition = PROCESS_DEFINITIONS[ProcessType.SUPPLIER_COMPLIANCE]
    process = _runner.run_verify_only(documents, definition)
    return process.to_dict()
