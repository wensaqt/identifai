import os
import random
import tempfile
from datetime import date

from dataset.company import generate_company
from dataset.documents import (
    generate_attestation_siret,
    generate_attestation_urssaf,
    generate_attestation_urssaf_expired,
    generate_devis,
    generate_facture,
    generate_kbis,
    generate_payment,
    generate_rib,
    generate_urssaf_declaration,
)


def _gen(fake, generator, *args, **kwargs):
    """Call a generator into a temp file and return (metadata, filepath)."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    meta = generator(*args, fake, path, **kwargs)
    return meta, path


class TestFacture:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client)

        assert meta["type"] == "invoice"
        assert meta["siret_emetteur"] == company.siret
        assert meta["nom_emetteur"] == company.name
        assert meta["nom_client"] == client.name
        assert meta["tva_rate"] == 0.20
        assert meta["montant_tva"] == round(meta["montant_ht"] * 0.20, 2)
        assert meta["montant_ttc"] == round(meta["montant_ht"] + meta["montant_tva"], 2)
        assert meta["statut_paiement"] == "unpaid"
        assert meta["reference_paiement"] is None
        assert "date_emission" in meta
        assert "date_prestation" in meta
        assert os.path.getsize(path) > 0
        os.unlink(path)

    def test_numero_format(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client)
        assert meta["invoice_id"].startswith("F-")
        os.unlink(path)

    def test_paid_with_reference(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client,
                          statut_paiement="paid", reference_paiement="PAY-001")
        assert meta["statut_paiement"] == "paid"
        assert meta["reference_paiement"] == "PAY-001"
        os.unlink(path)

    def test_override_tva(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client, override_tva=999.99)
        assert meta["montant_tva"] == 999.99
        os.unlink(path)


class TestDevis:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_devis, company, client)

        assert meta["type"] == "devis"
        assert meta["siret_emetteur"] == company.siret
        assert "date_validite" in meta
        assert meta["date_validite"] > meta["date_emission"]
        assert meta["montant_ttc"] == round(meta["montant_ht"] * 1.20, 2)
        os.unlink(path)


class TestPayment:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_payment, company, client)

        assert meta["type"] == "payment"
        assert "payment_id" in meta
        assert meta["payment_id"].startswith("PAY-")
        assert "date_paiement" in meta
        assert meta["montant"] > 0
        assert meta["emetteur"] == client.name
        assert meta["destinataire"] == company.name
        assert meta["reference_facture"] is None
        assert meta["methode"] in ("virement", "prélèvement", "chèque", "carte bancaire")
        os.unlink(path)

    def test_with_invoice_reference(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_payment, company, client,
                          invoice_id="F-2025-0001", montant=1500.00)
        assert meta["reference_facture"] == "F-2025-0001"
        assert meta["montant"] == 1500.00
        os.unlink(path)


class TestUrssafDeclaration:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_urssaf_declaration, company)

        assert meta["type"] == "urssaf_declaration"
        assert "periode" in meta
        assert meta["periode"].count("-T") == 1
        assert meta["chiffre_affaires_declare"] > 0
        assert "date_declaration" in meta
        assert meta["siret"] == company.siret
        os.unlink(path)

    def test_with_forced_ca(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_urssaf_declaration, company, chiffre_affaires=42000.00)
        assert meta["chiffre_affaires_declare"] == 42000.00
        os.unlink(path)


class TestAttestationSiret:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_attestation_siret, company)

        assert meta["type"] == "attestation_siret"
        assert meta["siret"] == company.siret
        assert meta["siren"] == company.siren
        assert meta["company_name"] == company.name
        os.unlink(path)


class TestAttestationUrssaf:
    def test_valid_not_expired(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_attestation_urssaf, company)

        assert meta["type"] == "attestation_urssaf"
        assert meta["date_expiration"] > meta["date_delivrance"]
        assert "expired" not in meta
        os.unlink(path)

    def test_expired(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_attestation_urssaf_expired, company)

        assert meta["expired"] is True
        d_del = date.fromisoformat(meta["date_delivrance"])
        d_exp = date.fromisoformat(meta["date_expiration"])
        assert (d_exp - d_del).days == 180
        os.unlink(path)


class TestKbis:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_kbis, company)

        assert meta["type"] == "kbis"
        assert meta["siret"] == company.siret
        assert meta["rcs"] == company.rcs
        os.unlink(path)


class TestRib:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        meta, path = _gen(fake, generate_rib, company)

        assert meta["type"] == "rib"
        assert meta["titulaire"] == company.name
        assert meta["iban"] == company.iban
        assert meta["bic"] == company.bic
        os.unlink(path)
