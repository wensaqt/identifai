from enum import StrEnum


class AnomalyType(StrEnum):
    MISSING_FIELD = "missing_field"
    INVALID_FORMAT = "invalid_format"
    MISSING_DOCUMENT = "missing_document"
    SIRET_MISMATCH = "siret_mismatch"
    EXPIRED_ATTESTATION = "expired_attestation"
    TVA_MISMATCH = "tva_mismatch"
    PAYMENT_AMOUNT_MISMATCH = "payment_amount_mismatch"
    ORPHAN_PAYMENT = "orphan_payment"
    MISSING_PAYMENT = "missing_payment"
    UNDECLARED_REVENUE = "undeclared_revenue"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
