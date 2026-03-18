# Backward-compatible re-exports from factories.company
from .factories.company import CompanyFactory, CompanyIdentity  # noqa: F401

from faker import Faker


def generate_company(fake: Faker) -> CompanyIdentity:
    return CompanyFactory(fake).create()


def with_wrong_siret(company: CompanyIdentity, fake: Faker) -> CompanyIdentity:
    return CompanyFactory(fake).with_wrong_siret(company)


def with_wrong_iban(company: CompanyIdentity, fake: Faker) -> CompanyIdentity:
    return CompanyFactory(fake).with_wrong_iban(company)
