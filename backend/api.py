import logging
from datetime import datetime, timezone

from classifier import classify_document
from consts.process import ProcessStatus, ProcessType
from db import ProcessRepository
from extractor import extract_fields
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models.process_definition import PROCESS_DEFINITIONS
from ocr import extract_text
from process_runner import ProcessRunner
from validation.completeness import CompletenessValidator
from validation.structure import validate_document
from validation.upload import UploadValidator

logger = logging.getLogger(__name__)

router = APIRouter()

_repo = ProcessRepository()
_runner = ProcessRunner(repo=_repo)
_completeness = CompletenessValidator()
_upload = UploadValidator()


def _process_document(file_bytes: bytes, filename: str) -> dict:
    result = extract_text(file_bytes, filename)
    result["doc_type"] = classify_document(result["text"])
    result["fields"] = extract_fields(result["text"], result["doc_type"])
    result["validation"] = validate_document(result["doc_type"], result["fields"])
    return result


@router.get("/health")
def health():
    return {"status": "ok"}


# ── Process CRUD ─────────────────────────────────────────────────────────────


@router.post("/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    doc_types: str = Form(None),
    process_type: str = Form("supplier_compliance"),
):
    """Full pipeline: OCR + classify + extract + validate + verify → Process."""
    try:
        pt = ProcessType(process_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")
    if pt not in PROCESS_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")
    definition = PROCESS_DEFINITIONS[pt]
    expected_map = _upload.build_expected_map(files, doc_types)

    # Phase 1 : OCR + classify pour vérifier la complétude
    classified = []
    for file in files:
        file_bytes = await file.read()
        error = _upload.validate_file(file, file_bytes)
        if error:
            raise HTTPException(status_code=400, detail=error)
        result = extract_text(file_bytes, file.filename)
        result["doc_type"] = classify_document(result["text"])
        classified.append((result, file_bytes))

    provided = {r["doc_type"] for r, _ in classified}
    missing = _completeness.find_missing(provided, definition)
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
    _runner.inject_anomalies(process, _upload.detect_type_mismatches(classified, expected_map))
    return process.to_dict()


@router.get("/processes/{process_id}")
def get_process(process_id: str):
    """Retrieve a process by ID."""
    process = _repo.find_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return process.to_dict()


@router.get("/processes")
def list_processes():
    """List all active (non-deleted) processes."""
    return [p.to_dict() for p in _repo.find_active()]


@router.put("/processes/{process_id}")
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
    expected_map = _upload.build_expected_map(files, doc_types)

    classified = []
    for file in files:
        file_bytes = await file.read()
        error = _upload.validate_file(file, file_bytes)
        if error:
            raise HTTPException(status_code=400, detail=error)
        result = extract_text(file_bytes, file.filename)
        result["doc_type"] = classify_document(result["text"])
        classified.append((result, file_bytes))

    provided = {r["doc_type"] for r, _ in classified}
    missing = _completeness.find_missing(provided, definition)
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
    _runner.inject_anomalies(updated, _upload.detect_type_mismatches(classified, expected_map))
    return updated.to_dict()


@router.delete("/processes/{process_id}")
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


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Single file: OCR + classify + extract + validate."""
    file_bytes = await file.read()
    error = _upload.validate_file(file, file_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return _process_document(file_bytes, file.filename)


@router.post("/verify")
async def verify(documents: list[dict], process_type: str = "supplier_compliance"):
    """Cross-document verification on pre-processed results → Process."""
    try:
        pt = ProcessType(process_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")
    if pt not in PROCESS_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown process type: {process_type}")
    definition = PROCESS_DEFINITIONS[pt]
    process = _runner.run_verify_only(documents, definition)
    return process.to_dict()
