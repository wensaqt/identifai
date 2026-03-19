from __future__ import annotations

from dataclasses import dataclass

from consts.doc_types import DocType
from consts.process import ProcessType


@dataclass(frozen=True)
class ProcessDefinition:
    process_type: ProcessType
    required_doc_types: frozenset[str]


SUPPLIER_COMPLIANCE = ProcessDefinition(
    process_type=ProcessType.SUPPLIER_COMPLIANCE,
    required_doc_types=frozenset(
        {
            DocType.INVOICE,
            DocType.SIRET_CERTIFICATE,
            DocType.URSSAF_CERTIFICATE,
            DocType.COMPANY_REGISTRATION,
            DocType.BANK_ACCOUNT_DETAILS,
            DocType.PAYMENT,
            DocType.URSSAF_DECLARATION,
        }
    ),
)

PROCESS_DEFINITIONS: dict[ProcessType, ProcessDefinition] = {
    ProcessType.SUPPLIER_COMPLIANCE: SUPPLIER_COMPLIANCE,
}
