from __future__ import annotations

import logging
import re

from consts.doc_types import DocType
from consts.patterns import (
    CLASSIFY_ATTESTATION_SIRET,
    CLASSIFY_ATTESTATION_URSSAF,
    CLASSIFY_DEVIS,
    CLASSIFY_FACTURE,
    CLASSIFY_KBIS,
    CLASSIFY_PAYMENT,
    CLASSIFY_RIB,
    CLASSIFY_URSSAF_DECLARATION,
)

logger = logging.getLogger(__name__)

# Rules checked top-to-bottom; first match wins. More specific rules first.
_RULES: list[tuple[str, list[str]]] = [
    (DocType.URSSAF_DECLARATION, CLASSIFY_URSSAF_DECLARATION),
    (DocType.ATTESTATION_URSSAF, CLASSIFY_ATTESTATION_URSSAF),
    (DocType.ATTESTATION_SIRET, CLASSIFY_ATTESTATION_SIRET),
    (DocType.KBIS, CLASSIFY_KBIS),
    (DocType.RIB, CLASSIFY_RIB),
    (DocType.PAYMENT, CLASSIFY_PAYMENT),
    (DocType.FACTURE, CLASSIFY_FACTURE),
    (DocType.DEVIS, CLASSIFY_DEVIS),
]


class DocumentClassifier:

    def classify(self, text: str) -> str | None:
        text_lower = text.lower()

        for doc_type, patterns in _RULES:
            if all(re.search(p, text_lower) for p in patterns):
                logger.info("[CLASSIFY] doc_type=%s", doc_type)
                return doc_type

        logger.warning("[CLASSIFY] Aucun type identifié")
        return None


_classifier = DocumentClassifier()


def classify_document(text: str) -> str | None:
    return _classifier.classify(text)
