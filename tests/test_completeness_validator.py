"""Tests for CompletenessValidator."""
from consts.anomalies import AnomalyType, Severity
from models.process_definition import SUPPLIER_COMPLIANCE, ANNUAL_DECLARATION
from validators.completeness import CompletenessValidator


class TestFindMissing:
    def setup_method(self):
        self._validator = CompletenessValidator()

    def test_all_provided_returns_empty(self):
        provided = set(SUPPLIER_COMPLIANCE.required_doc_types)
        assert self._validator.find_missing(provided, SUPPLIER_COMPLIANCE) == []

    def test_partial_returns_sorted_missing(self):
        provided = {"invoice", "payment"}
        missing = self._validator.find_missing(provided, SUPPLIER_COMPLIANCE)
        assert len(missing) == 5
        assert missing == sorted(missing)

    def test_empty_returns_all_required(self):
        missing = self._validator.find_missing(set(), SUPPLIER_COMPLIANCE)
        assert len(missing) == len(SUPPLIER_COMPLIANCE.required_doc_types)

    def test_annual_all_provided(self):
        provided = set(ANNUAL_DECLARATION.required_doc_types)
        assert self._validator.find_missing(provided, ANNUAL_DECLARATION) == []

    def test_annual_partial(self):
        provided = {"invoice"}
        missing = self._validator.find_missing(provided, ANNUAL_DECLARATION)
        assert len(missing) == 2
        assert "urssaf_certificate" in missing
        assert "urssaf_declaration" in missing


class TestCheckMissingAsAnomalies:
    def setup_method(self):
        self._validator = CompletenessValidator()

    def test_complete_docs_no_anomalies(self):
        docs = [{"doc_type": dt} for dt in SUPPLIER_COMPLIANCE.required_doc_types]
        anomalies = self._validator.check_missing_as_anomalies(docs, SUPPLIER_COMPLIANCE)
        assert anomalies == []

    def test_missing_docs_produce_error_anomalies(self):
        docs = [{"doc_type": "invoice"}]
        anomalies = self._validator.check_missing_as_anomalies(docs, SUPPLIER_COMPLIANCE)
        assert len(anomalies) >= 1
        for a in anomalies:
            assert a.type == AnomalyType.MISSING_DOCUMENT
            assert a.severity == Severity.ERROR
            assert a.document_refs == []

    def test_annual_missing_produces_correct_count(self):
        docs = [{"doc_type": "invoice"}]
        anomalies = self._validator.check_missing_as_anomalies(docs, ANNUAL_DECLARATION)
        assert len(anomalies) == 2
