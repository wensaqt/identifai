import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient  # noqa: E402

# Stub out doctr (not installed locally) before importing backend.
_ocr_mock = MagicMock()
_ocr_mock.extract_text = MagicMock()

for mod_name in ("doctr", "doctr.io", "doctr.models"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = ModuleType(mod_name)

sys.modules["ocr"] = _ocr_mock

from main import app, _repo  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    """Drop the test collection before each test."""
    _repo._col.drop()
    yield
    _repo._col.drop()


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestOcrEndpoint:
    def test_rejects_unsupported_type(self, client):
        r = client.post("/ocr", files={"file": ("test.txt", b"hello", "text/plain")})
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_rejects_oversized_file(self, client):
        big = b"x" * (20 * 1024 * 1024 + 1)
        r = client.post("/ocr", files={"file": ("big.pdf", big, "application/pdf")})
        assert r.status_code == 400
        assert "20 MB" in r.json()["detail"]

    def test_accepts_pdf(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf",
            "pages": 1,
            "text": "hello world",
            "pages_text": ["hello world"],
        }
        r = client.post(
            "/ocr", files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["text"] == "hello world"
        assert "fields" in data
        assert "doc_type" in data
        assert "validation" in data

    def test_pipeline_classify_then_extract(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "facture.pdf",
            "pages": 1,
            "text": "FACTURE N° F-2025-0042 SIRET : 10433218196001 TVA : FR59104332181 Date : 02/09/2025 Total HT : 100.00 € Total TTC : 120.00 €",
            "pages_text": ["..."],
        }
        r = client.post(
            "/ocr", files={"file": ("facture.pdf", b"%PDF-1.4 fake", "application/pdf")}
        )
        data = r.json()
        assert data["doc_type"] == "facture"
        assert "siret_emetteur" in data["fields"]
        assert data["fields"]["tva"] == "FR59104332181"
        assert data["validation"]["is_valid"] is True


class TestAnalyzeEndpoint:
    def test_returns_process_shape(self, client):
        _ocr_mock.extract_text.side_effect = [
            {
                "filename": "facture.pdf",
                "pages": 1,
                "text": "FACTURE N° F-2025-0001 SIRET : 11111111111111 Date : 01/01/2025 Total HT : 100.00 € Total TTC : 120.00 €",
                "pages_text": ["..."],
            },
            {
                "filename": "attestation.pdf",
                "pages": 1,
                "text": "AVIS DE SITUATION AU RÉPERTOIRE SIRENE SIRET : 22222222222222",
                "pages_text": ["..."],
            },
        ]
        r = client.post(
            "/analyze",
            files=[
                ("files", ("facture.pdf", b"%PDF", "application/pdf")),
                ("files", ("attestation.pdf", b"%PDF", "application/pdf")),
            ],
        )
        assert r.status_code == 200
        data = r.json()
        # Process shape
        assert "id" in data
        assert data["type"] == "conformite_fournisseur"
        assert data["status"] in ("valid", "error")
        assert "created_at" in data
        assert len(data["documents"]) == 2
        assert data["documents"][0]["doc_type"] == "facture"
        assert data["documents"][1]["doc_type"] == "attestation_siret"
        # SIRET mismatch between facture and attestation
        assert any(a["type"] == "siret_mismatch" for a in data["anomalies"])
        _ocr_mock.extract_text.side_effect = None

    def test_process_persisted_in_db(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf",
            "pages": 1,
            "text": "hello world",
            "pages_text": ["hello world"],
        }
        r = client.post(
            "/analyze",
            files=[("files", ("test.pdf", b"%PDF", "application/pdf"))],
        )
        process_id = r.json()["id"]
        # Should be retrievable
        r2 = client.get(f"/processes/{process_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == process_id

    def test_rejects_bad_file_in_batch(self, client):
        r = client.post(
            "/analyze",
            files=[
                ("files", ("test.txt", b"hello", "text/plain")),
            ],
        )
        assert r.status_code == 400


class TestGetProcess:
    def test_not_found(self, client):
        r = client.get("/processes/nonexistent")
        assert r.status_code == 404

    def test_found(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        r = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        pid = r.json()["id"]
        r2 = client.get(f"/processes/{pid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == pid
        assert r2.json()["type"] == "conformite_fournisseur"


class TestListProcesses:
    def test_empty(self, client):
        r = client.get("/processes")
        assert r.status_code == 200
        assert r.json() == []

    def test_lists_active_only(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        # Create two processes
        r1 = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        r2 = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        # Cancel one
        client.delete(f"/processes/{r1.json()['id']}")
        # Only one should be listed
        r = client.get("/processes")
        ids = [p["id"] for p in r.json()]
        assert r1.json()["id"] not in ids
        assert r2.json()["id"] in ids


class TestUpdateProcess:
    def test_rerun_pipeline(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        r = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        pid = r.json()["id"]

        # Re-run with same file
        r2 = client.put(
            f"/processes/{pid}",
            files=[("files", ("t.pdf", b"%PDF", "application/pdf"))],
        )
        assert r2.status_code == 200
        assert r2.json()["id"] == pid  # Same process ID

    def test_update_not_found(self, client):
        r = client.put(
            "/processes/nope",
            files=[("files", ("t.pdf", b"%PDF", "application/pdf"))],
        )
        assert r.status_code == 404

    def test_cannot_update_cancelled(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        r = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        pid = r.json()["id"]
        client.delete(f"/processes/{pid}")
        r2 = client.put(
            f"/processes/{pid}",
            files=[("files", ("t.pdf", b"%PDF", "application/pdf"))],
        )
        assert r2.status_code == 400


class TestCancelProcess:
    def test_cancel(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        r = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        pid = r.json()["id"]
        r2 = client.delete(f"/processes/{pid}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelled"
        assert "deleted_at" in r2.json()

    def test_cancel_not_found(self, client):
        r = client.delete("/processes/nope")
        assert r.status_code == 404

    def test_cancel_already_cancelled(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello", "pages_text": ["hello"],
        }
        r = client.post("/analyze", files=[("files", ("t.pdf", b"%PDF", "application/pdf"))])
        pid = r.json()["id"]
        client.delete(f"/processes/{pid}")
        r2 = client.delete(f"/processes/{pid}")
        assert r2.status_code == 400
