from enum import StrEnum


class DocType(StrEnum):
    INVOICE = "invoice"
    QUOTE = "quote"
    COMPANY_REGISTRATION = "company_registration"
    SIRET_CERTIFICATE = "siret_certificate"
    URSSAF_CERTIFICATE = "urssaf_certificate"
    BANK_ACCOUNT_DETAILS = "bank_account_details"
    PAYMENT = "payment"
    URSSAF_DECLARATION = "urssaf_declaration"


ATTESTATION_TYPES = {
    DocType.SIRET_CERTIFICATE,
    DocType.URSSAF_CERTIFICATE,
    DocType.COMPANY_REGISTRATION,
}
