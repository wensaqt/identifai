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
    generate_rib,
)


def _gen(fake, generator, *args):
    """Call a generator into a temp file and return (metadata, filepath)."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    meta = generator(*args, fake, path)
    return meta, path


class TestFacture:
    def test_metadata_fields(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client)

        assert meta["type"] == "facture"
        assert meta["siret_emetteur"] == company.siret
        assert meta["siret_client"] == client.siret
        assert meta["tva"] == company.tva
        assert meta["montant_ttc"] == round(meta["montant_ht"] * 1.20, 2)
        assert "date_emission" in meta
        assert os.path.getsize(path) > 0
        os.unlink(path)

    def test_numero_format(self, fake):
        random.seed(42)
        company = generate_company(fake)
        client = generate_company(fake)
        meta, path = _gen(fake, generate_facture, company, client)

        assert meta["numero"].startswith("F-")
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
        # Delivery must be 8-14 months ago, expiration = delivery + 180 days
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
