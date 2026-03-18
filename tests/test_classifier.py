import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from classifier import classify_document


class TestInvoice:
    def test_simple(self):
        assert classify_document("FACTURE N° F-2025-0042") == "invoice"

    def test_with_company_info(self):
        text = "FACTURE Guilbert S.A. SIRET : 10433218196001 Total TTC : 1200.00 €"
        assert classify_document(text) == "invoice"

    def test_case_insensitive(self):
        assert classify_document("facture n° 123") == "invoice"


class TestQuote:
    def test_simple(self):
        assert classify_document("DEVIS N° D-2025-0001") == "quote"

    def test_with_validity(self):
        text = "DEVIS Validité : 30 jours Total HT : 500.00 €"
        assert classify_document(text) == "quote"


class TestSiretCertificate:
    def test_avis_situation(self):
        text = "AVIS DE SITUATION AU RÉPERTOIRE SIRENE SIRET : 72604782880829"
        assert classify_document(text) == "siret_certificate"

    def test_repertoire_siret(self):
        text = "Répertoire SIRET — Institut National de la Statistique"
        assert classify_document(text) == "siret_certificate"


class TestUrssafCertificate:
    def test_attestation_vigilance(self):
        text = "URSSAF ATTESTATION DE VIGILANCE est à jour de ses obligations"
        assert classify_document(text) == "urssaf_certificate"

    def test_urssaf_attestation_reversed(self):
        text = "Attestation de l'URSSAF confirmant la situation"
        assert classify_document(text) == "urssaf_certificate"


class TestCompanyRegistration:
    def test_extrait_kbis(self):
        text = "EXTRAIT K BIS Greffe du Tribunal de Commerce de Paris"
        assert classify_document(text) == "company_registration"

    def test_greffe_only(self):
        text = "Greffe du tribunal SIREN 123456789"
        assert classify_document(text) == "company_registration"


class TestBankAccountDetails:
    def test_rib_iban(self):
        text = "RELEVÉ D'IDENTITÉ BANCAIRE IBAN : FR7630006000011234567890189"
        assert classify_document(text) == "bank_account_details"

    def test_rib_short(self):
        text = "RIB Titulaire : Guilbert S.A. IBAN FR76 3000 6000"
        assert classify_document(text) == "bank_account_details"


class TestPayment:
    def test_confirmation_paiement(self):
        text = "CONFIRMATION DE PAIEMENT Référence PAY-2025-0001 Montant 1200.00 €"
        assert classify_document(text) == "payment"

    def test_case_insensitive(self):
        text = "confirmation de paiement effectuée"
        assert classify_document(text) == "payment"


class TestUrssafDeclaration:
    def test_declaration_ca(self):
        text = "URSSAF DÉCLARATION DE CHIFFRE D'AFFAIRES Période 2025-T1"
        assert classify_document(text) == "urssaf_declaration"

    def test_without_accent(self):
        text = "URSSAF Declaration de chiffre d'affaires"
        assert classify_document(text) == "urssaf_declaration"


class TestUnknown:
    def test_empty(self):
        assert classify_document("") is None

    def test_garbage(self):
        assert classify_document("lorem ipsum dolor sit amet") is None


class TestPriority:
    def test_urssaf_declaration_over_attestation(self):
        text = "URSSAF DÉCLARATION DE CHIFFRE D'AFFAIRES attestation"
        assert classify_document(text) == "urssaf_declaration"

    def test_urssaf_over_siret(self):
        text = "URSSAF ATTESTATION DE VIGILANCE SIRET : 10433218196001 Répertoire"
        assert classify_document(text) == "urssaf_certificate"

    def test_invoice_with_payment_stays_invoice(self):
        """An invoice mentioning 'paiement' must not be classified as payment."""
        text = "FACTURE Statut : PAID Réf. paiement : PAY-2025-0001"
        assert classify_document(text) == "invoice"

    def test_invoice_not_quote(self):
        text = "FACTURE référence au devis D-2025-001"
        assert classify_document(text) == "invoice"
