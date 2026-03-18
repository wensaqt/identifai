from __future__ import annotations

from dataclasses import dataclass

from consts.doc_types import DocType
from consts.process import ProcessType


@dataclass(frozen=True)
class ProcessDefinition:
    process_type: ProcessType
    required_doc_types: frozenset[str]


CONFORMITE_FOURNISSEUR = ProcessDefinition(
    process_type=ProcessType.CONFORMITE_FOURNISSEUR,
    required_doc_types=frozenset({
        DocType.FACTURE,
        DocType.ATTESTATION_SIRET,
        DocType.ATTESTATION_URSSAF,
        DocType.KBIS,
        DocType.RIB,
        DocType.PAYMENT,
        DocType.URSSAF_DECLARATION,
    }),
)

PROCESS_DEFINITIONS: dict[ProcessType, ProcessDefinition] = {
    ProcessType.CONFORMITE_FOURNISSEUR: CONFORMITE_FOURNISSEUR,
}
