from enum import StrEnum


class DocType(StrEnum):
    FACTURE = "facture"
    INVOICE = "invoice"
    DEVIS = "devis"
    ATTESTATION_SIRET = "attestation_siret"
    ATTESTATION_URSSAF = "attestation_urssaf"
    KBIS = "kbis"
    RIB = "rib"
    PAYMENT = "payment"
    URSSAF_DECLARATION = "urssaf_declaration"


# Groups used for cross-document checks
INVOICE_TYPES = {DocType.FACTURE, DocType.INVOICE, DocType.DEVIS}
ATTESTATION_TYPES = {DocType.ATTESTATION_SIRET, DocType.ATTESTATION_URSSAF, DocType.KBIS}
