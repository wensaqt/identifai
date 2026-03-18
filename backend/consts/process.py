from enum import StrEnum


class ProcessType(StrEnum):
    CONFORMITE_FOURNISSEUR = "conformite_fournisseur"


class ProcessStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    ERROR = "error"
    CANCELLED = "cancelled"
