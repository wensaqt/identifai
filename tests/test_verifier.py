import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from verifier import verify_documents


def _doc(filename, doc_type, fields):
    return {"filename": filename, "doc_type": doc_type, "fields": fields}


class TestSiretCoherence:
    def test_matching_sirets_no_issue(self):
        docs = [
            _doc("facture.pdf", "facture", {"siret": "10433218196001"}),
            _doc("attestation.pdf", "attestation_urssaf", {"siret": "10433218196001"}),
        ]
        issues = verify_documents(docs)
        assert not any(i["type"] == "siret_mismatch" for i in issues)

    def test_mismatched_sirets_raises_error(self):
        docs = [
            _doc("facture.pdf", "facture", {"siret": "10433218196001"}),
            _doc("attestation.pdf", "attestation_urssaf", {"siret": "99999999999999"}),
        ]
        issues = verify_documents(docs)
        errors = [i for i in issues if i["type"] == "siret_mismatch"]
        assert len(errors) == 1
        assert errors[0]["severity"] == "error"

    def test_no_attestation_skips_check(self):
        docs = [_doc("facture.pdf", "facture", {"siret": "10433218196001"})]
        issues = verify_documents(docs)
        assert not any(i["type"] == "siret_mismatch" for i in issues)


class TestExpiredAttestation:
    def test_expired_attestation(self):
        docs = [_doc("att.pdf", "attestation_urssaf", {"siret": "10433218196001", "date_expiration": "01/01/2020"})]
        issues = verify_documents(docs)
        errors = [i for i in issues if i["type"] == "expired_attestation"]
        assert len(errors) == 1
        assert errors[0]["severity"] == "error"

    def test_valid_attestation_no_issue(self):
        docs = [_doc("att.pdf", "attestation_urssaf", {"siret": "10433218196001", "date_expiration": "01/01/2099"})]
        issues = verify_documents(docs)
        assert not any(i["type"] == "expired_attestation" for i in issues)

    def test_no_expiration_date_skipped(self):
        docs = [_doc("att.pdf", "attestation_urssaf", {"siret": "10433218196001"})]
        issues = verify_documents(docs)
        assert not any(i["type"] == "expired_attestation" for i in issues)


class TestMissingFields:
    def test_missing_field_on_facture(self):
        docs = [_doc("facture.pdf", "facture", {"siret": "10433218196001"})]
        issues = verify_documents(docs)
        warnings = [i for i in issues if i["type"] == "missing_fields"]
        assert len(warnings) == 1
        assert "montant_ht" in warnings[0]["message"]

    def test_complete_facture_no_warning(self):
        docs = [_doc("facture.pdf", "facture", {
            "siret": "10433218196001",
            "montant_ht": "100.00",
            "montant_ttc": "120.00",
            "date_emission": "01/01/2025",
        })]
        issues = verify_documents(docs)
        assert not any(i["type"] == "missing_fields" for i in issues)

    def test_rib_missing_iban(self):
        docs = [_doc("rib.pdf", "rib", {})]
        issues = verify_documents(docs)
        warnings = [i for i in issues if i["type"] == "missing_fields"]
        assert len(warnings) == 1
        assert "iban" in warnings[0]["message"]
