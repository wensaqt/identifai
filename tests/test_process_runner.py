"""Tests for ProcessRunner."""
from consts.anomalies import AnomalyType, Severity
from consts.process import ProcessStatus
from models.process_definition import SUPPLIER_COMPLIANCE, ANNUAL_DECLARATION
from process_runner import ProcessRunner


def _make_doc(doc_type, filename, fields):
    return {"doc_type": doc_type, "filename": filename, "fields": fields}


class TestProcessRunner:
    def setup_method(self):
        self._runner = ProcessRunner()
        self._definition = SUPPLIER_COMPLIANCE

    def test_valid_process_with_complete_docs(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
            _make_doc("siret_certificate", "siret.pdf", {"siret": "12345678901234"}),
            _make_doc("urssaf_certificate", "urssaf.pdf", {
                "siret": "12345678901234", "date_expiration": "31/12/2027",
            }),
            _make_doc("company_registration", "kbis.pdf", {"siret": "12345678901234", "siren": "123456789"}),
            _make_doc("bank_account_details", "rib.pdf", {"iban": "FR7630001007941234567890185"}),
            _make_doc("payment", "payment.pdf", {
                "montant": "1200.00", "date_paiement": "15/01/2025",
                "reference_facture": "F-2025-0001",
            }),
            _make_doc("urssaf_declaration", "declaration.pdf", {
                "siret": "12345678901234", "periode": "2025-T1",
                "chiffre_affaires_declare": "1000.00", "date_declaration": "01/04/2025",
            }),
        ]
        process = self._runner.run(docs, self._definition)
        assert process.type == "supplier_compliance"
        assert process.status == ProcessStatus.VALID
        assert len(process.documents) == 7
        errors = [a for a in process.anomalies if a.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_missing_documents_produce_anomalies(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
        ]
        process = self._runner.run(docs, self._definition)
        assert process.status == ProcessStatus.ERROR
        missing_doc_anomalies = [a for a in process.anomalies if a.type == AnomalyType.MISSING_DOCUMENT]
        assert len(missing_doc_anomalies) >= 1

    def test_siret_mismatch_detected(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "11111111111111",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
            _make_doc("siret_certificate", "siret.pdf", {"siret": "22222222222222"}),
        ]
        process = self._runner.run(docs, self._definition)
        assert any(a.type == AnomalyType.SIRET_MISMATCH for a in process.anomalies)

    def test_process_has_id_and_created_at(self):
        docs = [_make_doc("invoice", "f.pdf", {"invoice_id": "F-001"})]
        process = self._runner.run(docs, self._definition)
        assert process.id is not None
        assert len(process.id) == 8
        assert process.created_at is not None

    def test_verify_only(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
        ]
        process = self._runner.run_verify_only(docs, self._definition)
        assert process.type == "supplier_compliance"
        assert process.status in (ProcessStatus.VALID, ProcessStatus.ERROR)


class TestProcessRunnerAnnualDeclaration:
    def setup_method(self):
        self._runner = ProcessRunner()
        self._definition = ANNUAL_DECLARATION

    def test_valid_annual_declaration(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
            _make_doc("urssaf_certificate", "urssaf.pdf", {
                "siret": "12345678901234", "date_expiration": "31/12/2027",
            }),
            _make_doc("urssaf_declaration", "declaration.pdf", {
                "siret": "12345678901234", "periode": "2025-T1",
                "chiffre_affaires_declare": "1000.00", "date_declaration": "01/04/2025",
            }),
        ]
        process = self._runner.run(docs, self._definition)
        assert process.type == "annual_declaration"
        assert process.status == ProcessStatus.VALID
        assert len(process.documents) == 3
        errors = [a for a in process.anomalies if a.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_missing_urssaf_certificate(self):
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00", "date_emission": "01/01/2025",
            }),
            _make_doc("urssaf_declaration", "declaration.pdf", {
                "siret": "12345678901234", "periode": "2025-T1",
                "chiffre_affaires_declare": "1000.00", "date_declaration": "01/04/2025",
            }),
        ]
        process = self._runner.run(docs, self._definition)
        assert process.status == ProcessStatus.ERROR
        missing = [a for a in process.anomalies if a.type == AnomalyType.MISSING_DOCUMENT]
        assert len(missing) == 1
        assert "urssaf_certificate" in missing[0].message

    def test_no_payment_checks_run(self):
        """Invoice marked as paid without payment doc should NOT trigger payment anomalies."""
        docs = [
            _make_doc("invoice", "invoice.pdf", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "12345678901234",
                "montant_ht": "1000.00", "montant_ttc": "1200.00",
                "date_emission": "01/01/2025", "statut_paiement": "paid",
            }),
            _make_doc("urssaf_certificate", "urssaf.pdf", {
                "siret": "12345678901234", "date_expiration": "31/12/2027",
            }),
            _make_doc("urssaf_declaration", "declaration.pdf", {
                "siret": "12345678901234", "periode": "2025-T1",
                "chiffre_affaires_declare": "1000.00", "date_declaration": "01/04/2025",
            }),
        ]
        process = self._runner.run(docs, self._definition)
        payment_anomalies = [
            a for a in process.anomalies
            if a.type in (AnomalyType.MISSING_PAYMENT, AnomalyType.ORPHAN_PAYMENT, AnomalyType.PAYMENT_AMOUNT_MISMATCH)
        ]
        assert len(payment_anomalies) == 0
