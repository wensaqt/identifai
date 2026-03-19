from enum import StrEnum


class ProcessType(StrEnum):
    SUPPLIER_COMPLIANCE = "supplier_compliance"


class ProcessStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    ERROR = "error"
    CANCELLED = "cancelled"
