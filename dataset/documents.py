# Backward-compatible re-exports from factories.documents
from faker import Faker

from .factories.company import CompanyIdentity
from .factories.documents import (  # noqa: F401
    AttestationSiretFactory,
    AttestationUrssafFactory,
    DevisFactory,
    InvoiceFactory,
    KbisFactory,
    PaymentFactory,
    RibFactory,
    UrssafDeclarationFactory,
)


def generate_facture(company: CompanyIdentity, client: CompanyIdentity,
                     fake: Faker, filepath: str, **kwargs) -> dict:
    return InvoiceFactory(fake).create(company, client, filepath, **kwargs)


def generate_devis(company: CompanyIdentity, client: CompanyIdentity,
                   fake: Faker, filepath: str) -> dict:
    return DevisFactory(fake).create(company, client, filepath)


def generate_attestation_siret(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    return AttestationSiretFactory(fake).create(company, filepath)


def generate_attestation_urssaf(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    return AttestationUrssafFactory(fake).create(company, filepath)


def generate_attestation_urssaf_expired(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    return AttestationUrssafFactory(fake).create_expired(company, filepath)


def generate_kbis(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    return KbisFactory(fake).create(company, filepath)


def generate_rib(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    return RibFactory(fake).create(company, filepath)


def generate_payment(company: CompanyIdentity, client: CompanyIdentity,
                     fake: Faker, filepath: str, **kwargs) -> dict:
    return PaymentFactory(fake).create(company, client, filepath, **kwargs)


def generate_urssaf_declaration(company: CompanyIdentity, fake: Faker, filepath: str, **kwargs) -> dict:
    return UrssafDeclarationFactory(fake).create(company, filepath, **kwargs)
