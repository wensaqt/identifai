import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from classifier import classify_document


class TestFacture:
    def test_simple(self):
        assert classify_document("FACTURE N° F-2025-0042") == "facture"

    def test_with_company_info(self):
        text = "FACTURE Guilbert S.A. SIRET : 10433218196001 Total TTC : 1200.00 €"
        assert classify_document(text) == "facture"

    def test_case_insensitive(self):
        assert classify_document("facture n° 123") == "facture"


class TestDevis:
    def test_simple(self):
        assert classify_document("DEVIS N° D-2025-0001") == "devis"

    def test_with_validity(self):
        text = "DEVIS Validité : 30 jours Total HT : 500.00 €"
        assert classify_document(text) == "devis"


class TestAttestationSiret:
    def test_avis_situation(self):
        text = "AVIS DE SITUATION AU RÉPERTOIRE SIRENE SIRET : 72604782880829"
        assert classify_document(text) == "attestation_siret"

    def test_repertoire_siret(self):
        text = "Répertoire SIRET — Institut National de la Statistique"
        assert classify_document(text) == "attestation_siret"


class TestAttestationUrssaf:
    def test_attestation_vigilance(self):
        text = "URSSAF ATTESTATION DE VIGILANCE est à jour de ses obligations"
        assert classify_document(text) == "attestation_urssaf"

    def test_urssaf_attestation_reversed(self):
        text = "Attestation de l'URSSAF confirmant la situation"
        assert classify_document(text) == "attestation_urssaf"


class TestKbis:
    def test_extrait_kbis(self):
        text = "EXTRAIT K BIS Greffe du Tribunal de Commerce de Paris"
        assert classify_document(text) == "kbis"

    def test_tribunal_commerce(self):
        text = "Tribunal de Commerce de Lyon — extrait d'immatriculation"
        assert classify_document(text) == "kbis"

    def test_greffe_only(self):
        text = "Greffe du tribunal SIREN 123456789"
        assert classify_document(text) == "kbis"


class TestRib:
    def test_rib_iban(self):
        text = "RELEVÉ D'IDENTITÉ BANCAIRE IBAN : FR7630006000011234567890189"
        assert classify_document(text) == "rib"

    def test_rib_short(self):
        text = "RIB Titulaire : Guilbert S.A. IBAN FR76 3000 6000"
        assert classify_document(text) == "rib"


class TestUnknown:
    def test_empty(self):
        assert classify_document("") is None

    def test_garbage(self):
        assert classify_document("lorem ipsum dolor sit amet") is None

    def test_ambiguous_no_match(self):
        assert classify_document("SIRET : 12345678901234 Total : 100€") is None


class TestPriority:
    def test_urssaf_over_siret(self):
        """URSSAF attestation mentions SIRET too — must not be classified as attestation_siret."""
        text = "URSSAF ATTESTATION DE VIGILANCE SIRET : 10433218196001 Répertoire"
        assert classify_document(text) == "attestation_urssaf"

    def test_facture_not_devis(self):
        text = "FACTURE référence au devis D-2025-001"
        assert classify_document(text) == "facture"
