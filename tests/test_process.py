"""Tests for backend Process models and enums."""
import pytest

from consts.anomalies import AnomalyType, Severity
from consts.process import ProcessStatus, ProcessType
from consts.process_definitions import SUPPLIER_COMPLIANCE, PROCESS_DEFINITIONS
from process import Process, ProcessAnomaly, ProcessDocument


class TestEnums:
    def test_process_type_values(self):
        assert ProcessType.SUPPLIER_COMPLIANCE == "supplier_compliance"

    def test_process_status_values(self):
        assert ProcessStatus.PENDING == "pending"
        assert ProcessStatus.VALID == "valid"
        assert ProcessStatus.ERROR == "error"
        assert ProcessStatus.CANCELLED == "cancelled"

    def test_anomaly_type_values(self):
        assert AnomalyType.SIRET_MISMATCH == "siret_mismatch"
        assert AnomalyType.MISSING_FIELD == "missing_field"
        assert AnomalyType.MISSING_DOCUMENT == "missing_document"

    def test_severity_values(self):
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"


class TestProcessDefinition:
    def test_supplier_compliance_exists(self):
        assert ProcessType.SUPPLIER_COMPLIANCE in PROCESS_DEFINITIONS

    def test_required_doc_types(self):
        d = SUPPLIER_COMPLIANCE
        assert "invoice" in d.required_doc_types
        assert "company_registration" in d.required_doc_types
        assert "bank_account_details" in d.required_doc_types
        assert "payment" in d.required_doc_types

    def test_definition_is_frozen(self):
        with pytest.raises(AttributeError):
            SUPPLIER_COMPLIANCE.process_type = "other"


class TestProcessAnomaly:
    def test_to_dict_basic(self):
        a = ProcessAnomaly(
            type=AnomalyType.SIRET_MISMATCH,
            severity=Severity.ERROR,
            message="SIRET mismatch",
            document_refs=["invoice.pdf"],
        )
        d = a.to_dict()
        assert d["type"] == "siret_mismatch"
        assert d["severity"] == "error"
        assert d["document_refs"] == ["invoice.pdf"]
        assert "field" not in d

    def test_to_dict_with_field(self):
        a = ProcessAnomaly(
            type=AnomalyType.MISSING_FIELD,
            severity=Severity.WARNING,
            message="Missing field",
            document_refs=["doc.pdf"],
            field="siret",
        )
        d = a.to_dict()
        assert d["field"] == "siret"


class TestProcessDocument:
    def test_to_dict(self):
        d = ProcessDocument("invoice", "invoice.pdf", {"siret": "12345"}).to_dict()
        assert d["doc_type"] == "invoice"
        assert d["filename"] == "invoice.pdf"
        assert d["fields"]["siret"] == "12345"


class TestProcess:
    def test_to_dict_structure(self):
        p = Process(
            id="abc123",
            type="supplier_compliance",
            status="valid",
            documents=[ProcessDocument("invoice", "f.pdf", {})],
            anomalies=[],
            created_at="2026-03-18T00:00:00",
        )
        d = p.to_dict()
        assert d["id"] == "abc123"
        assert d["type"] == "supplier_compliance"
        assert d["status"] == "valid"
        assert len(d["documents"]) == 1
        assert d["anomalies"] == []
        assert d["created_at"] == "2026-03-18T00:00:00"
        assert "deleted_at" not in d

    def test_to_dict_with_deleted_at(self):
        p = Process(
            id="abc123",
            type="supplier_compliance",
            status="cancelled",
            documents=[],
            anomalies=[],
            created_at="2026-03-18T00:00:00",
            deleted_at="2026-03-18T12:00:00",
        )
        d = p.to_dict()
        assert d["status"] == "cancelled"
        assert d["deleted_at"] == "2026-03-18T12:00:00"
