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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()

    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB limit")

    result = extract_text(file_bytes, file.filename)
    result["doc_type"] = classify_document(result["text"])
    result["fields"] = extract_fields(result["text"], result["doc_type"])
    result["validation"] = validate_document(result["doc_type"], result["fields"])
    return result


@app.post("/verify")
async def verify(documents: list[dict]):
    """Verify a batch of OCR results for inter-document coherence."""
    return {"issues": verify_documents(documents)}
