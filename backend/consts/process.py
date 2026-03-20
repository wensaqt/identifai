from enum import StrEnum


class ProcessType(StrEnum):
    SUPPLIER_COMPLIANCE = "supplier_compliance"
    ANNUAL_DECLARATION = "annual_declaration"


class ProcessStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    ERROR = "error"
    CANCELLED = "cancelled"
