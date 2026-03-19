import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from consts.process import ProcessType
from validation.cross_document import verify_documents


def _doc(filename, doc_type, fields):
    return {"filename": filename, "doc_type": doc_type, "fields": fields}


class TestSiretCoherence:
    def test_matching_sirets_no_issue(self):
        docs = [
            _doc("invoice.pdf", "invoice", {"siret_emetteur": "12345678901234"}),
            _doc("siret.pdf", "siret_certificate", {"siret": "12345678901234"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "siret_mismatch"]
        assert len(issues) == 0

    def test_mismatched_sirets(self):
        docs = [
            _doc("invoice.pdf", "invoice", {"siret_emetteur": "12345678901234"}),
            _doc("siret.pdf", "siret_certificate", {"siret": "99999999999999"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "siret_mismatch"]
        assert len(issues) == 1

    def test_no_attestation_skips(self):
        docs = [_doc("invoice.pdf", "invoice", {"siret_emetteur": "12345678901234"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "siret_mismatch"]
        assert len(issues) == 0


class TestExpiredAttestation:
    def test_expired(self):
        docs = [_doc("att.pdf", "urssaf_certificate", {"siret": "12345678901234", "date_expiration": "01/01/2020"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "expired_attestation"]
        assert len(issues) == 1

    def test_valid(self):
        docs = [_doc("att.pdf", "urssaf_certificate", {"siret": "12345678901234", "date_expiration": "01/01/2099"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "expired_attestation"]
        assert len(issues) == 0

    def test_no_expiration_skipped(self):
        docs = [_doc("att.pdf", "urssaf_certificate", {"siret": "12345678901234"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "expired_attestation"]
        assert len(issues) == 0


class TestTvaCoherence:
    def test_correct_tva(self):
        docs = [_doc("f.pdf", "invoice", {
            "montant_ht": "1000.00", "montant_tva": "200.00", "tva_rate": "0.20",
        })]
        issues = [i for i in verify_documents(docs) if i["type"] == "tva_mismatch"]
        assert len(issues) == 0

    def test_wrong_tva(self):
        docs = [_doc("f.pdf", "invoice", {
            "montant_ht": "1000.00", "montant_tva": "500.00", "tva_rate": "0.20",
        })]
        issues = [i for i in verify_documents(docs) if i["type"] == "tva_mismatch"]
        assert len(issues) == 1

    def test_missing_fields_skipped(self):
        docs = [_doc("f.pdf", "invoice", {"montant_ht": "1000.00"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "tva_mismatch"]
        assert len(issues) == 0


class TestPaymentAmount:
    def test_matching(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001", "montant_ttc": "1200.00"}),
            _doc("p.pdf", "payment", {"reference_facture": "F-2025-0001", "montant": "1200.00"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "payment_amount_mismatch"]
        assert len(issues) == 0

    def test_mismatch(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001", "montant_ttc": "1200.00"}),
            _doc("p.pdf", "payment", {"reference_facture": "F-2025-0001", "montant": "800.00"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "payment_amount_mismatch"]
        assert len(issues) == 1


class TestOrphanPayments:
    def test_no_orphan(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001"}),
            _doc("p.pdf", "payment", {"reference_facture": "F-2025-0001"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "orphan_payment"]
        assert len(issues) == 0

    def test_orphan_detected(self):
        docs = [_doc("p.pdf", "payment", {"reference_facture": "F-0000-0000"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "orphan_payment"]
        assert len(issues) == 1

    def test_no_reference_not_orphan(self):
        docs = [_doc("p.pdf", "payment", {"montant": "100.00"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "orphan_payment"]
        assert len(issues) == 0


class TestMissingPayment:
    def test_paid_with_payment_no_issue(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001", "statut_paiement": "paid"}),
            _doc("p.pdf", "payment", {"reference_facture": "F-2025-0001", "montant": "100.00"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "missing_payment"]
        assert len(issues) == 0

    def test_no_payment_for_invoice(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001", "statut_paiement": "paid"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "missing_payment"]
        assert len(issues) == 1

    def test_unpaid_no_issue(self):
        docs = [
            _doc("f.pdf", "invoice", {"invoice_id": "F-2025-0001", "statut_paiement": "unpaid"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "missing_payment"]
        assert len(issues) == 0


class TestDeclaredRevenue:
    def test_correct(self):
        docs = [
            _doc("f.pdf", "invoice", {"montant_ht": "10000.00"}),
            _doc("d.pdf", "urssaf_declaration", {"chiffre_affaires_declare": "10000.00"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "undeclared_revenue"]
        assert len(issues) == 0

    def test_underdeclared(self):
        docs = [
            _doc("f.pdf", "invoice", {"montant_ht": "10000.00"}),
            _doc("d.pdf", "urssaf_declaration", {"chiffre_affaires_declare": "5000.00"}),
        ]
        issues = [i for i in verify_documents(docs) if i["type"] == "undeclared_revenue"]
        assert len(issues) == 1

    def test_no_invoices_skipped(self):
        docs = [_doc("d.pdf", "urssaf_declaration", {"chiffre_affaires_declare": "5000.00"})]
        issues = [i for i in verify_documents(docs) if i["type"] == "undeclared_revenue"]
        assert len(issues) == 0


class TestProcessTypeFiltering:
    """Verify that process_type controls which checks run."""

    def _docs_with_siret_mismatch_and_payment(self):
        return [
            _doc("invoice.pdf", "invoice", {
                "invoice_id": "F-2025-0001", "siret_emetteur": "11111111111111",
                "montant_ht": "1000.00", "montant_tva": "500.00", "tva_rate": "0.20",
                "montant_ttc": "1200.00", "statut_paiement": "paid",
            }),
            _doc("siret.pdf", "siret_certificate", {"siret": "22222222222222"}),
            _doc("urssaf.pdf", "urssaf_certificate", {
                "siret": "22222222222222", "date_expiration": "01/01/2020",
            }),
            _doc("declaration.pdf", "urssaf_declaration", {
                "chiffre_affaires_declare": "100.00",
            }),
        ]

    def test_annual_declaration_skips_siret_mismatch(self):
        docs = self._docs_with_siret_mismatch_and_payment()
        issues = verify_documents(docs, ProcessType.ANNUAL_DECLARATION)
        assert not any(i["type"] == "siret_mismatch" for i in issues)

    def test_annual_declaration_skips_payment_checks(self):
        docs = self._docs_with_siret_mismatch_and_payment()
        issues = verify_documents(docs, ProcessType.ANNUAL_DECLARATION)
        payment_types = {"missing_payment", "orphan_payment", "payment_amount_mismatch"}
        assert not any(i["type"] in payment_types for i in issues)

    def test_annual_declaration_runs_tva_expired_revenue(self):
        docs = self._docs_with_siret_mismatch_and_payment()
        issues = verify_documents(docs, ProcessType.ANNUAL_DECLARATION)
        types = {i["type"] for i in issues}
        assert "tva_mismatch" in types
        assert "expired_attestation" in types
        assert "undeclared_revenue" in types

    def test_none_process_type_runs_all_checks(self):
        docs = self._docs_with_siret_mismatch_and_payment()
        issues = verify_documents(docs, None)
        types = {i["type"] for i in issues}
        assert "siret_mismatch" in types
        assert "missing_payment" in types
