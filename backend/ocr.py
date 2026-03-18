from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from PIL import Image

logger = logging.getLogger(__name__)


class OcrService:

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = ocr_predictor(det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True)
        return self._model

    @staticmethod
    def _pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        return images

    def extract(self, file_bytes: bytes, filename: str) -> dict:
        model = self._get_model()
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            images = self._pdf_to_images(file_bytes)
            tmp_paths = []
            for img in images:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name)
                tmp_paths.append(tmp.name)
            doc = DocumentFile.from_images(tmp_paths)
        else:
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

        logger.info("[OCR] fichier=%s pages=%d chars=%d", filename, len(pages_text), len(full_text))

        return {
            "filename": filename,
            "pages": len(pages_text),
            "text": full_text,
            "pages_text": pages_text,
        }


_ocr_service = OcrService()


def extract_text(file_bytes: bytes, filename: str) -> dict:
    return _ocr_service.extract(file_bytes, filename)
