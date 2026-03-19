import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from models.document_fields import (
    DOC_TYPE_MODELS,
    BankAccountDetailsFields,
    InvoiceFields,
    PaymentFields,
    UrssafCertificateFields,
    UrssafDeclarationFields,
)


class TestToDict:
    def test_excludes_none(self):
        f = InvoiceFields(siret_emetteur="12345678901234", montant_ht="100.00")
        d = f.to_dict()
        assert d == {"siret_emetteur": "12345678901234", "montant_ht": "100.00"}

    def test_empty(self):
        f = BankAccountDetailsFields()
        assert f.to_dict() == {}


class TestMissingFields:
    def test_all_present(self):
        f = InvoiceFields(
            invoice_id="F-2025-0001",
            siret_emetteur="12345678901234",
            montant_ht="100.00",
            montant_ttc="120.00",
            date_emission="2025-01-01",
        )
        assert f.missing_fields() == []

    def test_some_missing(self):
        f = InvoiceFields(siret_emetteur="12345678901234")
        missing = f.missing_fields()
        assert "invoice_id" in missing
        assert "montant_ht" in missing
        assert "montant_ttc" in missing
        assert "date_emission" in missing
        assert "siret_emetteur" not in missing

    def test_bank_account_missing_iban(self):
        f = BankAccountDetailsFields(bic="BNPAFRPP")
        assert f.missing_fields() == ["iban"]

    def test_urssaf_certificate(self):
        f = UrssafCertificateFields(siret="12345678901234")
        assert f.missing_fields() == ["date_expiration"]

    def test_payment(self):
        f = PaymentFields()
        assert set(f.missing_fields()) == {"montant", "date_paiement"}

    def test_urssaf_declaration(self):
        f = UrssafDeclarationFields(siret="12345678901234")
        missing = f.missing_fields()
        assert "periode" in missing
        assert "chiffre_affaires_declare" in missing
        assert "date_declaration" in missing


class TestRegistry:
    def test_invoice_maps_correctly(self):
        assert DOC_TYPE_MODELS["invoice"] is InvoiceFields

    def test_all_types_registered(self):
        expected = {
            "invoice", "quote", "siret_certificate",
            "urssaf_certificate", "company_registration",
            "bank_account_details", "payment", "urssaf_declaration",
        }
        assert set(DOC_TYPE_MODELS.keys()) == expected
