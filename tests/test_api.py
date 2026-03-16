import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# Stub out doctr (not installed locally) before importing backend.
# fitz (PyMuPDF) IS installed so we don't mock it.
_ocr_mock = MagicMock()
_ocr_mock.extract_text = MagicMock()

for mod_name in ("doctr", "doctr.io", "doctr.models"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = ModuleType(mod_name)

# Replace the ocr module with our mock so main.py doesn't load the real one
sys.modules["ocr"] = _ocr_mock

from main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestOcrEndpoint:
    def test_rejects_unsupported_type(self, client):
        r = client.post(
            "/ocr",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_rejects_oversized_file(self, client):
        big = b"x" * (20 * 1024 * 1024 + 1)
        r = client.post(
            "/ocr",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        assert r.status_code == 400
        assert "20 MB" in r.json()["detail"]

    def test_accepts_pdf(self, client):
        mock_result = {
            "filename": "test.pdf",
            "pages": 1,
            "text": "hello world",
            "pages_text": ["hello world"],
        }
        _ocr_mock.extract_text.return_value = mock_result
        r = client.post(
            "/ocr",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert r.status_code == 200
        assert r.json()["text"] == "hello world"
        assert "fields" in r.json()
        assert "doc_type" in r.json()

    def test_fields_extracted_from_text(self, client):
        mock_result = {
            "filename": "facture.pdf",
            "pages": 1,
            "text": "SIRET : 10433218196001 TVA : FR59104332181 Date : 02/09/2025 Total HT : 100.00 € Total TTC : 120.00 €",
            "pages_text": ["SIRET : 10433218196001 TVA : FR59104332181 Date : 02/09/2025 Total HT : 100.00 € Total TTC : 120.00 €"],
        }
        _ocr_mock.extract_text.return_value = mock_result
        r = client.post(
            "/ocr",
            files={"file": ("facture.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert r.status_code == 200
        fields = r.json()["fields"]
        assert fields["siret"] == "10433218196001"
        assert fields["tva"] == "FR59104332181"
        assert fields["date_emission"] == "02/09/2025"
        assert fields["montant_ht"] == "100.00"
        assert fields["montant_ttc"] == "120.00"

    def test_accepts_jpeg(self, client):
        mock_result = {
            "filename": "photo.jpg",
            "pages": 1,
            "text": "some text",
            "pages_text": ["some text"],
        }
        _ocr_mock.extract_text.return_value = mock_result
        r = client.post(
            "/ocr",
            files={"file": ("photo.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
        assert r.status_code == 200

    def test_accepts_png(self, client):
        mock_result = {
            "filename": "scan.png",
            "pages": 1,
            "text": "text",
            "pages_text": ["text"],
        }
        _ocr_mock.extract_text.return_value = mock_result
        r = client.post(
            "/ocr",
            files={"file": ("scan.png", b"\x89PNG", "image/png")},
        )
        assert r.status_code == 200
