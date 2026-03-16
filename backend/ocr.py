from __future__ import annotations

import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from PIL import Image

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = ocr_predictor(det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True)
    return _model


def _pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images


def extract_text(file_bytes: bytes, filename: str) -> dict:
    model = _get_model()
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        images = _pdf_to_images(file_bytes)
        # Save images to temp files for DocTR
        tmp_paths = []
        for img in images:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            tmp_paths.append(tmp.name)
        doc = DocumentFile.from_images(tmp_paths)
    else:
        # Direct image input
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(file_bytes)
        tmp.flush()
        doc = DocumentFile.from_images([tmp.name])

    result = model(doc)

    pages_text = []
    for page in result.pages:
        words = []
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    words.append(word.value)
        pages_text.append(" ".join(words))

    full_text = "\n".join(pages_text)

    return {
        "filename": filename,
        "pages": len(pages_text),
        "text": full_text,
        "pages_text": pages_text,
    }
