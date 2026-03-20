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

from main import app  # noqa: E402
from api import _repo  # noqa: E402

# ── OCR stubs for a complete 7-doc set ────────────────────────────────────────

_FULL_OCR_RESPONSES = [
    {"filename": "invoice.pdf", "pages": 1, "pages_text": ["..."],
     "text": "FACTURE N° F-2025-0001 SIRET : 12345678901234 Date : 01/01/2025 Total HT : 1000.00 € Total TTC : 1200.00 €"},
    {"filename": "siret.pdf", "pages": 1, "pages_text": ["..."],
     "text": "AVIS DE SITUATION AU RÉPERTOIRE SIRENE SIRET : 12345678901234"},
    {"filename": "urssaf.pdf", "pages": 1, "pages_text": ["..."],
     "text": "URSSAF ATTESTATION DE VIGILANCE SIRET : 12345678901234 Expiration : 31/12/2027"},
    {"filename": "kbis.pdf", "pages": 1, "pages_text": ["..."],
     "text": "EXTRAIT K BIS Greffe du Tribunal SIRET : 12345678901234 SIREN : 123456789"},
    {"filename": "rib.pdf", "pages": 1, "pages_text": ["..."],
     "text": "RELEVÉ D'IDENTITÉ BANCAIRE IBAN : FR7630001007941234567890185"},
    {"filename": "payment.pdf", "pages": 1, "pages_text": ["..."],
     "text": "CONFIRMATION DE PAIEMENT PAY-2025-0001 Date : 15/01/2025 Montant : 1200.00 € Réf. facture : F-2025-0001"},
    {"filename": "declaration.pdf", "pages": 1, "pages_text": ["..."],
     "text": "URSSAF DÉCLARATION DE CHIFFRE D'AFFAIRES SIRET : 12345678901234 Période : 2025-T1 Chiffre d'affaires déclaré : 1000.00 € Date de déclaration : 01/04/2025"},
]

_FULL_UPLOAD_FILES = [
    ("files", ("invoice.pdf", b"%PDF", "application/pdf")),
    ("files", ("siret.pdf", b"%PDF", "application/pdf")),
    ("files", ("urssaf.pdf", b"%PDF", "application/pdf")),
    ("files", ("kbis.pdf", b"%PDF", "application/pdf")),
    ("files", ("rib.pdf", b"%PDF", "application/pdf")),
    ("files", ("payment.pdf", b"%PDF", "application/pdf")),
    ("files", ("declaration.pdf", b"%PDF", "application/pdf")),
]


def _setup_full_ocr():
    _ocr_mock.extract_text.side_effect = list(_FULL_OCR_RESPONSES)


def _teardown_ocr():
    _ocr_mock.extract_text.side_effect = None
    _ocr_mock.extract_text.reset_mock()


def _create_process(client):
    """Helper: create a complete process and return its ID."""
    _setup_full_ocr()
    r = client.post("/analyze", files=list(_FULL_UPLOAD_FILES))
    _teardown_ocr()
    assert r.status_code == 200
    return r.json()["id"]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
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

    def test_rejects_oversized_file(self, client):
        big = b"x" * (20 * 1024 * 1024 + 1)
        r = client.post("/ocr", files={"file": ("big.pdf", big, "application/pdf")})
        assert r.status_code == 400

    def test_accepts_pdf(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "test.pdf", "pages": 1,
            "text": "hello world", "pages_text": ["hello world"],
        }
        r = client.post("/ocr", files={"file": ("test.pdf", b"%PDF", "application/pdf")})
        assert r.status_code == 200
        data = r.json()
        assert data["text"] == "hello world"
        assert "fields" in data
        assert "doc_type" in data

    def test_pipeline_classify_then_extract(self, client):
        _ocr_mock.extract_text.return_value = {
            "filename": "facture.pdf", "pages": 1,
            "text": "FACTURE N° F-2025-0042 SIRET : 10433218196001 TVA : FR59104332181 Date : 02/09/2025 Total HT : 100.00 € Total TTC : 120.00 €",
            "pages_text": ["..."],
        }
        r = client.post("/ocr", files={"file": ("facture.pdf", b"%PDF", "application/pdf")})
        data = r.json()
        assert data["doc_type"] == "invoice"
        assert "siret_emetteur" in data["fields"]


class TestAnalyzeEndpoint:
    def test_returns_process_shape(self, client):
        _setup_full_ocr()
        r = client.post("/analyze", files=list(_FULL_UPLOAD_FILES))
        _teardown_ocr()
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["type"] == "supplier_compliance"
        assert data["status"] in ("valid", "error")
        assert "created_at" in data
        assert len(data["documents"]) == 7

    def test_rejects_missing_documents(self, client):
        _ocr_mock.extract_text.side_effect = [
            {"filename": "invoice.pdf", "pages": 1, "pages_text": ["..."],
             "text": "FACTURE N° F-2025-0001 SIRET : 12345678901234"},
        ]
        r = client.post("/analyze", files=[
            ("files", ("invoice.pdf", b"%PDF", "application/pdf")),
        ])
        _teardown_ocr()
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["error"] == "missing_documents"
        assert len(detail["missing"]) > 0

    def test_process_persisted_in_db(self, client):
        pid = _create_process(client)
        r = client.get(f"/processes/{pid}")
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_rejects_bad_file_in_batch(self, client):
        r = client.post("/analyze", files=[
            ("files", ("test.txt", b"hello", "text/plain")),
        ])
        assert r.status_code == 400


class TestGetProcess:
    def test_not_found(self, client):
        r = client.get("/processes/nonexistent")
        assert r.status_code == 404

    def test_found(self, client):
        pid = _create_process(client)
        r = client.get(f"/processes/{pid}")
        assert r.status_code == 200
        assert r.json()["type"] == "supplier_compliance"


class TestListProcesses:
    def test_empty(self, client):
        r = client.get("/processes")
        assert r.status_code == 200
        assert r.json() == []

    def test_lists_active_only(self, client):
        pid1 = _create_process(client)
        pid2 = _create_process(client)
        client.delete(f"/processes/{pid1}")
        r = client.get("/processes")
        ids = [p["id"] for p in r.json()]
        assert pid1 not in ids
        assert pid2 in ids


class TestUpdateProcess:
    def test_rerun_pipeline(self, client):
        pid = _create_process(client)
        _setup_full_ocr()
        r = client.put(f"/processes/{pid}", files=list(_FULL_UPLOAD_FILES))
        _teardown_ocr()
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_update_rejects_missing_documents(self, client):
        pid = _create_process(client)
        _ocr_mock.extract_text.side_effect = [
            {"filename": "invoice.pdf", "pages": 1, "pages_text": ["..."],
             "text": "FACTURE N° F-2025-0001"},
        ]
        r = client.put(f"/processes/{pid}", files=[
            ("files", ("invoice.pdf", b"%PDF", "application/pdf")),
        ])
        _teardown_ocr()
        assert r.status_code == 400
        assert r.json()["detail"]["error"] == "missing_documents"

    def test_update_not_found(self, client):
        r = client.put("/processes/nope", files=[
            ("files", ("t.pdf", b"%PDF", "application/pdf")),
        ])
        assert r.status_code == 404

    def test_cannot_update_cancelled(self, client):
        pid = _create_process(client)
        client.delete(f"/processes/{pid}")
        r = client.put(f"/processes/{pid}", files=[
            ("files", ("t.pdf", b"%PDF", "application/pdf")),
        ])
        assert r.status_code == 400


class TestCancelProcess:
    def test_cancel(self, client):
        pid = _create_process(client)
        r = client.delete(f"/processes/{pid}")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"
        assert "deleted_at" in r.json()

    def test_cancel_not_found(self, client):
        r = client.delete("/processes/nope")
        assert r.status_code == 404

    def test_cancel_already_cancelled(self, client):
        pid = _create_process(client)
        client.delete(f"/processes/{pid}")
        r = client.delete(f"/processes/{pid}")
        assert r.status_code == 400


class TestDocTypeMismatch:
    """doc_types field: mismatch between declared and classified type."""

    def test_mismatch_adds_warning_anomaly(self, client):
        """Sending wrong doc_type for a file should produce a doc_type_mismatch warning."""
        import json
        _setup_full_ocr()
        # Declare invoice file as payment (wrong)
        wrong_types = ["payment", "siret_certificate", "urssaf_certificate",
                       "company_registration", "bank_account_details", "payment", "urssaf_declaration"]
        r = client.post(
            "/analyze",
            files=list(_FULL_UPLOAD_FILES),
            data={"doc_types": json.dumps(wrong_types)},
        )
        _teardown_ocr()
        assert r.status_code == 200
        anomaly_types = [a["type"] for a in r.json()["anomalies"]]
        assert "doc_type_mismatch" in anomaly_types

    def test_no_mismatch_when_types_correct(self, client):
        """Sending correct doc_types should not produce doc_type_mismatch anomalies."""
        import json
        _setup_full_ocr()
        correct_types = ["invoice", "siret_certificate", "urssaf_certificate",
                         "company_registration", "bank_account_details", "payment", "urssaf_declaration"]
        r = client.post(
            "/analyze",
            files=list(_FULL_UPLOAD_FILES),
            data={"doc_types": json.dumps(correct_types)},
        )
        _teardown_ocr()
        assert r.status_code == 200
        anomaly_types = [a["type"] for a in r.json()["anomalies"]]
        assert "doc_type_mismatch" not in anomaly_types

    def test_no_doc_types_field_still_works(self, client):
        """Omitting doc_types should not break the endpoint."""
        _setup_full_ocr()
        r = client.post("/analyze", files=list(_FULL_UPLOAD_FILES))
        _teardown_ocr()
        assert r.status_code == 200


# ── Annual Declaration OCR stubs ─────────────────────────────────────────────

_ANNUAL_OCR_RESPONSES = [
    {"filename": "invoice.pdf", "pages": 1, "pages_text": ["..."],
     "text": "FACTURE N° F-2025-0001 SIRET : 12345678901234 Date : 01/01/2025 Total HT : 1000.00 € Total TTC : 1200.00 €"},
    {"filename": "declaration.pdf", "pages": 1, "pages_text": ["..."],
     "text": "URSSAF DÉCLARATION DE CHIFFRE D'AFFAIRES SIRET : 12345678901234 Période : 2025-T1 Chiffre d'affaires déclaré : 1000.00 € Date de déclaration : 01/04/2025"},
    {"filename": "urssaf.pdf", "pages": 1, "pages_text": ["..."],
     "text": "URSSAF ATTESTATION DE VIGILANCE SIRET : 12345678901234 Expiration : 31/12/2027"},
]

_ANNUAL_UPLOAD_FILES = [
    ("files", ("invoice.pdf", b"%PDF", "application/pdf")),
    ("files", ("declaration.pdf", b"%PDF", "application/pdf")),
    ("files", ("urssaf.pdf", b"%PDF", "application/pdf")),
]


def _setup_annual_ocr():
    _ocr_mock.extract_text.side_effect = list(_ANNUAL_OCR_RESPONSES)


class TestAnalyzeAnnualDeclaration:
    def test_annual_3_docs_ok(self, client):
        _setup_annual_ocr()
        r = client.post(
            "/analyze",
            files=list(_ANNUAL_UPLOAD_FILES),
            data={"process_type": "annual_declaration"},
        )
        _teardown_ocr()
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "annual_declaration"
        assert len(data["documents"]) == 3

    def test_annual_missing_documents(self, client):
        _ocr_mock.extract_text.side_effect = [
            {"filename": "invoice.pdf", "pages": 1, "pages_text": ["..."],
             "text": "FACTURE N° F-2025-0001 SIRET : 12345678901234"},
        ]
        r = client.post(
            "/analyze",
            files=[("files", ("invoice.pdf", b"%PDF", "application/pdf"))],
            data={"process_type": "annual_declaration"},
        )
        _teardown_ocr()
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["error"] == "missing_documents"
        assert len(detail["missing"]) > 0

    def test_unknown_process_type(self, client):
        r = client.post(
            "/analyze",
            files=[("files", ("t.pdf", b"%PDF", "application/pdf"))],
            data={"process_type": "nonexistent"},
        )
        assert r.status_code == 400

    def test_default_process_type_is_supplier_compliance(self, client):
        _setup_full_ocr()
        r = client.post("/analyze", files=list(_FULL_UPLOAD_FILES))
        _teardown_ocr()
        assert r.status_code == 200
        assert r.json()["type"] == "supplier_compliance"
