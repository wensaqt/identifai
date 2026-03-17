from __future__ import annotations

from dataclasses import dataclass, replace

from faker import Faker

_FORMES_JURIDIQUES = ["SAS", "SARL", "EURL", "SA", "SCI"]
_BANKS = ["BNP Paribas", "Société Générale", "Crédit Agricole",
          "Crédit Mutuel", "LCL", "Banque Populaire", "CIC"]
_CAPITALS = [1000, 5000, 10000, 50000, 100000]


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


class CompanyFactory:

    def __init__(self, fake: Faker):
        self._fake = fake

    def _compute_tva(self, siren: str) -> str:
        key = (12 + 3 * (int(siren) % 97)) % 97
        return f"FR{key:02d}{siren}"

    def create(self) -> CompanyIdentity:
        siren = self._fake.numerify("#########")
        siret = siren + self._fake.numerify("#####")
        city = self._fake.city()
        return CompanyIdentity(
            name=self._fake.company(),
            forme_juridique=self._fake.random_element(_FORMES_JURIDIQUES),
            siret=siret,
            siren=siren,
            tva=self._compute_tva(siren),
            address=self._fake.street_address(),
            zip_code=self._fake.postcode(),
            city=city,
            iban=self._fake.iban(),
            bic=self._fake.swift(),
            bank_name=self._fake.random_element(_BANKS),
            capital_social=self._fake.random_element(_CAPITALS),
            registration_date=self._fake.date_between(start_date="-10y", end_date="-1y").isoformat(),
            rcs=f"RCS {city} {siren}",
        )

    def with_wrong_siret(self, company: CompanyIdentity) -> CompanyIdentity:
        new_siren = self._fake.numerify("#########")
        new_siret = new_siren + self._fake.numerify("#####")
        return replace(
            company,
            siren=new_siren,
            siret=new_siret,
            tva=self._compute_tva(new_siren),
            rcs=f"RCS {company.city} {new_siren}",
        )

    def with_wrong_iban(self, company: CompanyIdentity) -> CompanyIdentity:
        return replace(
            company,
            iban=self._fake.iban(),
            bic=self._fake.swift(),
            bank_name=self._fake.random_element(_BANKS),
        )
