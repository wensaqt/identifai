import random

from faker import Faker

from dataset.company import (
    CompanyIdentity,
    generate_company,
    with_wrong_iban,
    with_wrong_siret,
)


def test_generate_company_fields(fake):
    company = generate_company(fake)

    assert isinstance(company, CompanyIdentity)
    assert len(company.siren) == 9
    assert len(company.siret) == 14
    assert company.siret.startswith(company.siren)
    assert company.tva.startswith("FR")
    assert company.forme_juridique in ("SAS", "SARL", "EURL", "SA", "SCI")
    assert company.capital_social in (1000, 5000, 10000, 50000, 100000)
    assert company.rcs.startswith("RCS ")


def test_tva_checksum(fake):
    """TVA intra key must follow the French MOD97 formula."""
    company = generate_company(fake)
    siren = int(company.siren)
    expected_key = (12 + 3 * (siren % 97)) % 97
    assert company.tva == f"FR{expected_key:02d}{company.siren}"


def test_with_wrong_siret(fake):
    random.seed(42)
    company = generate_company(fake)
    bad = with_wrong_siret(company, fake)

    assert bad.siret != company.siret
    assert bad.siren != company.siren
    assert bad.tva != company.tva
    # Non-identity fields stay the same
    assert bad.name == company.name
    assert bad.iban == company.iban


def test_with_wrong_iban(fake):
    random.seed(42)
    company = generate_company(fake)
    bad = with_wrong_iban(company, fake)

    assert bad.iban != company.iban
    # Identity fields stay the same
    assert bad.siret == company.siret
    assert bad.name == company.name


def test_deterministic_with_seed():
    """Same seed must produce the same company."""
    Faker.seed(99)
    fake1 = Faker("fr_FR")
    c1 = generate_company(fake1)

    Faker.seed(99)
    fake2 = Faker("fr_FR")
    c2 = generate_company(fake2)

    assert c1 == c2
