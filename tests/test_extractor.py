import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from extractor import extract_fields


class TestSiret:
    def test_extracts_siret(self):
        text = "SIRET : 10433218196001"
        assert extract_fields(text)["siret"] == "10433218196001"

    def test_extracts_siret_client(self):
        text = "SIRET fournisseur : 10433218196001 SIRET client : 75255341928327"
        fields = extract_fields(text)
        assert fields["siret"] == "10433218196001"
        assert fields["siret_client"] == "75255341928327"

    def test_no_siret_returns_empty(self):
        assert "siret" not in extract_fields("pas de siret ici")


class TestTva:
    def test_extracts_tva(self):
        text = "TVA : FR59104332181"
        assert extract_fields(text)["tva"] == "FR59104332181"

    def test_no_tva(self):
        assert "tva" not in extract_fields("SIRET : 10433218196001")


class TestMontants:
    def test_extracts_ht(self):
        text = "Total HT : 1 234,56 €"
        assert extract_fields(text)["montant_ht"] == "1234.56"

    def test_extracts_ttc(self):
        text = "Total TTC : 9876.54 €"
        assert extract_fields(text)["montant_ttc"] == "9876.54"

    def test_no_montants(self):
        fields = extract_fields("SIRET : 10433218196001")
        assert "montant_ht" not in fields
        assert "montant_ttc" not in fields


class TestDates:
    def test_date_emission_slash(self):
        text = "Date : 02/09/2025"
        assert extract_fields(text)["date_emission"] == "02/09/2025"

    def test_date_emission_iso(self):
        text = "Date d inscription : 2017-05-25"
        assert extract_fields(text)["date_emission"] == "2017-05-25"

    def test_date_expiration(self):
        text = "Expiration : 31/12/2025"
        assert extract_fields(text)["date_expiration"] == "31/12/2025"

    def test_no_date(self):
        assert "date_emission" not in extract_fields("SIRET : 10433218196001")


class TestIban:
    def test_extracts_iban(self):
        text = "IBAN : FR7630006000011234567890189"
        fields = extract_fields(text)
        assert "iban" in fields
        assert fields["iban"].startswith("FR76")


class TestFull:
    def test_facture(self):
        text = (
            "FACTURE Guilbert S.A. SIRET : 10433218196001 TVA : FR59104332181 "
            "Date : 02/09/2025 Client SIRET : 75255341928327 "
            "Total HT : 16904.98 € Total TTC : 20285.98 €"
        )
        fields = extract_fields(text)
        assert fields["siret"] == "10433218196001"
        assert fields["tva"] == "FR59104332181"
        assert fields["date_emission"] == "02/09/2025"
        assert fields["montant_ht"] == "16904.98"
        assert fields["montant_ttc"] == "20285.98"

    def test_attestation_siret(self):
        text = (
            "AVIS DE SITUATION AU RÉPERTOIRE SIRENE SIRET : 72604782880829 "
            "Date d inscription : 2017-05-25"
        )
        fields = extract_fields(text)
        assert fields["siret"] == "72604782880829"
        assert fields["date_emission"] == "2017-05-25"


class TestTypeAware:
    def test_facture_extracts_invoice_id(self):
        text = "FACTURE N° F-2025-0042 SIRET : 10433218196001"
        fields = extract_fields(text, doc_type="facture")
        assert fields["invoice_id"] == "F-2025-0042"

    def test_facture_remaps_siret(self):
        text = "SIRET : 10433218196001 Total HT : 100.00 €"
        fields = extract_fields(text, doc_type="facture")
        assert "siret_emetteur" in fields
        assert "siret" not in fields

    def test_attestation_keeps_siret(self):
        text = "SIRET : 10433218196001"
        fields = extract_fields(text, doc_type="attestation_siret")
        assert "siret" in fields
        assert "siret_emetteur" not in fields

    def test_backward_compat_no_doc_type(self):
        text = "SIRET : 10433218196001"
        fields = extract_fields(text)
        assert "siret" in fields


class TestTvaRate:
    def test_extracts_tva_rate(self):
        text = "FACTURE TVA 20% : 200.00 € Total HT : 1000.00 €"
        fields = extract_fields(text, doc_type="facture")
        assert fields["tva_rate"] == "0.2"

    def test_tva_rate_10(self):
        text = "TVA 10% : 50.00 €"
        fields = extract_fields(text, doc_type="facture")
        assert fields["tva_rate"] == "0.1"


class TestCleanAmount:
    def test_ocr_thousands_separator(self):
        """OCR may read 5,823.14 as 5.823.14 — extractor should handle it."""
        text = "Chiffre d'affaires déclaré : 5.823.14 € Période : 2025-T1 Date de déclaration : 01/04/2025 SIRET : 12345678901234"
        fields = extract_fields(text, doc_type="urssaf_declaration")
        assert fields["chiffre_affaires_declare"] == "5823.14"

    def test_normal_amount(self):
        text = "Total HT : 1234.56 €"
        fields = extract_fields(text, doc_type="facture")
        assert fields["montant_ht"] == "1234.56"


class TestPaymentExtraction:
    def test_extracts_payment_fields(self):
        text = (
            "CONFIRMATION DE PAIEMENT Référence PAY-2025-0042 "
            "Date : 15/03/2025 Montant : 1200.00 € "
            "Méthode : virement Réf. facture : F-2025-0001"
        )
        fields = extract_fields(text, doc_type="payment")
        assert fields["payment_id"] == "PAY-2025-0042"
        assert fields["montant"] == "1200.00"
        assert fields["reference_facture"] == "F-2025-0001"
        assert fields["date_paiement"] == "15/03/2025"
        assert fields["methode"] == "virement"


class TestDeclarationExtraction:
    def test_extracts_declaration_fields(self):
        text = (
            "URSSAF DÉCLARATION DE CHIFFRE D'AFFAIRES "
            "SIRET : 10433218196001 Période : 2025-T1 "
            "Chiffre d'affaires déclaré : 50000.00 € "
            "Date de déclaration : 01/04/2025"
        )
        fields = extract_fields(text, doc_type="urssaf_declaration")
        assert fields["siret"] == "10433218196001"
        assert fields["periode"] == "2025-T1"
        assert fields["chiffre_affaires_declare"] == "50000.00"
        assert fields["date_declaration"] == "01/04/2025"
