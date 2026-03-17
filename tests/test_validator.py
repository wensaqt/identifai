import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from validator import validate_completeness, validate_document, validate_format


class TestCompleteness:
    def test_complete_invoice(self):
        fields = {
            "siret_emetteur": "12345678901234",
            "montant_ht": "100.00",
            "montant_ttc": "120.00",
            "date_emission": "01/01/2025",
        }
        assert validate_completeness("facture", fields) == []

    def test_incomplete_invoice(self):
        fields = {"siret_emetteur": "12345678901234"}
        issues = validate_completeness("facture", fields)
        missing = [i["field"] for i in issues]
        assert "montant_ht" in missing
        assert "montant_ttc" in missing
        assert "date_emission" in missing

    def test_rib_missing_iban(self):
        issues = validate_completeness("rib", {"bic": "BNPAFRPP"})
        assert len(issues) == 1
        assert issues[0]["field"] == "iban"

    def test_unknown_type_returns_empty(self):
        assert validate_completeness("unknown", {}) == []

    def test_none_type_returns_empty(self):
        assert validate_completeness(None, {}) == []

    def test_payment_requires_montant_and_date(self):
        issues = validate_completeness("payment", {})
        missing = {i["field"] for i in issues}
        assert missing == {"montant", "date_paiement"}

    def test_urssaf_declaration(self):
        issues = validate_completeness("urssaf_declaration", {"siret": "12345678901234"})
        missing = {i["field"] for i in issues}
        assert "periode" in missing
        assert "chiffre_affaires_declare" in missing
        assert "date_declaration" in missing


class TestFormat:
    def test_valid_siret(self):
        assert validate_format({"siret": "12345678901234"}) == []

    def test_invalid_siret_too_short(self):
        issues = validate_format({"siret": "1234567890"})
        assert len(issues) == 1
        assert issues[0]["field"] == "siret"

    def test_invalid_siret_letters(self):
        issues = validate_format({"siret": "1234567890ABCD"})
        assert len(issues) == 1

    def test_valid_siren(self):
        assert validate_format({"siren": "123456789"}) == []

    def test_valid_tva(self):
        assert validate_format({"tva": "FR59104332181"}) == []

    def test_invalid_tva(self):
        issues = validate_format({"tva": "DE123456789"})
        assert len(issues) == 1

    def test_valid_iban(self):
        assert validate_format({"iban": "FR7630006000011234567890189"}) == []

    def test_valid_bic(self):
        assert validate_format({"bic": "BNPAFRPP"}) == []

    def test_valid_amount(self):
        assert validate_format({"montant_ht": "1234.56"}) == []

    def test_invalid_amount(self):
        issues = validate_format({"montant_ht": "abc"})
        assert len(issues) == 1

    def test_valid_date_slash(self):
        assert validate_format({"date_emission": "01/01/2025"}) == []

    def test_valid_date_iso(self):
        assert validate_format({"date_emission": "2025-01-01"}) == []

    def test_invalid_date(self):
        issues = validate_format({"date_emission": "January 1st"})
        assert len(issues) == 1

    def test_valid_periode(self):
        assert validate_format({"periode": "2025-T1"}) == []

    def test_invalid_periode(self):
        issues = validate_format({"periode": "2025-T5"})
        assert len(issues) == 1

    def test_unknown_field_ignored(self):
        assert validate_format({"nom_client": "Dupont"}) == []


class TestValidateDocument:
    def test_valid_document(self):
        fields = {
            "siret_emetteur": "12345678901234",
            "montant_ht": "100.00",
            "montant_ttc": "120.00",
            "date_emission": "2025-01-01",
        }
        result = validate_document("facture", fields)
        assert result["is_valid"] is True
        assert result["completeness"] == []
        assert result["format"] == []

    def test_missing_field_makes_invalid(self):
        result = validate_document("facture", {"siret_emetteur": "12345678901234"})
        assert result["is_valid"] is False
        assert len(result["completeness"]) > 0

    def test_bad_format_makes_invalid(self):
        fields = {
            "siret_emetteur": "BAD",
            "montant_ht": "100.00",
            "montant_ttc": "120.00",
            "date_emission": "2025-01-01",
        }
        result = validate_document("facture", fields)
        assert result["is_valid"] is False
        assert len(result["format"]) > 0
