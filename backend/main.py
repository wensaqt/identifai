import logging

from fastapi import FastAPI, File, HTTPException, UploadFile

from classifier import classify_document
from extractor import extract_fields
from ocr import extract_text
from validator import validate_document
from verifier import verify_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="IdentifAI API")

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB


def _validate_upload(file: UploadFile, file_bytes: bytes) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB limit")


def _process_document(file_bytes: bytes, filename: str) -> dict:
    result = extract_text(file_bytes, filename)
    result["doc_type"] = classify_document(result["text"])
    result["fields"] = extract_fields(result["text"], result["doc_type"])
    result["validation"] = validate_document(result["doc_type"], result["fields"])
    return result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)):
    """Full pipeline: OCR + classify + extract + validate + verify."""
    documents = []
    for file in files:
        file_bytes = await file.read()
        _validate_upload(file, file_bytes)
        documents.append(_process_document(file_bytes, file.filename))

    issues = verify_documents(documents)

    return {
        "documents": documents,
        "issues": issues,
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Single file: OCR + classify + extract + validate."""
    file_bytes = await file.read()
    _validate_upload(file, file_bytes)
    return _process_document(file_bytes, file.filename)


@app.post("/verify")
async def verify(documents: list[dict]):
    """Cross-document verification on pre-processed results."""
    return {"issues": verify_documents(documents)}
