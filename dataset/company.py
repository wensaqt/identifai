from dataclasses import dataclass, replace

from faker import Faker


@dataclass(frozen=True)
class CompanyIdentity:
    name: str
    forme_juridique: str
    siret: str
    siren: str
    tva: str
    address: str
    zip_code: str
    city: str
    iban: str
    bic: str
    bank_name: str
    capital_social: int
    registration_date: str
    rcs: str


def generate_company(fake: Faker) -> CompanyIdentity:
    siren = fake.numerify("#########")
    siret = siren + fake.numerify("#####")
    tva_key = (12 + 3 * (int(siren) % 97)) % 97
    tva = f"FR{tva_key:02d}{siren}"

    forme = fake.random_element(["SAS", "SARL", "EURL", "SA", "SCI"])
    city = fake.city()

    return CompanyIdentity(
        name=fake.company(),
        forme_juridique=forme,
        siret=siret,
        siren=siren,
        tva=tva,
        address=fake.street_address(),
        zip_code=fake.postcode(),
        city=city,
        iban=fake.iban(),
        bic=fake.swift(),
        bank_name=fake.random_element([
            "BNP Paribas", "Société Générale", "Crédit Agricole",
            "Crédit Mutuel", "LCL", "Banque Populaire", "CIC",
        ]),
        capital_social=fake.random_element([1000, 5000, 10000, 50000, 100000]),
        registration_date=fake.date_between(start_date="-10y", end_date="-1y").isoformat(),
        rcs=f"RCS {city} {siren}",
    )


def with_wrong_siret(company: CompanyIdentity, fake: Faker) -> CompanyIdentity:
    """Return a copy with a different SIRET/SIREN (breaks cross-document coherence)."""
    new_siren = fake.numerify("#########")
    new_siret = new_siren + fake.numerify("#####")
    tva_key = (12 + 3 * (int(new_siren) % 97)) % 97
    return replace(
        company,
        siren=new_siren,
        siret=new_siret,
        tva=f"FR{tva_key:02d}{new_siren}",
        rcs=f"RCS {company.city} {new_siren}",
    )


def with_wrong_iban(company: CompanyIdentity, fake: Faker) -> CompanyIdentity:
    """Return a copy with a different IBAN/BIC (RIB won't match facture payment info)."""
    return replace(
        company,
        iban=fake.iban(),
        bic=fake.swift(),
        bank_name=fake.random_element([
            "BNP Paribas", "Société Générale", "Crédit Agricole",
            "Crédit Mutuel", "LCL", "Banque Populaire", "CIC",
        ]),
    )
