from __future__ import annotations

import logging
import re

from consts.doc_types import DocType
from consts.patterns import (
    CLASSIFY_BANK_ACCOUNT_DETAILS,
    CLASSIFY_COMPANY_REGISTRATION,
    CLASSIFY_INVOICE,
    CLASSIFY_PAYMENT,
    CLASSIFY_QUOTE,
    CLASSIFY_SIRET_CERTIFICATE,
    CLASSIFY_URSSAF_CERTIFICATE,
    CLASSIFY_URSSAF_DECLARATION,
)

logger = logging.getLogger(__name__)

# Rules checked top-to-bottom; first match wins. More specific rules first.
_RULES: list[tuple[str, list[str]]] = [
    (DocType.URSSAF_DECLARATION, CLASSIFY_URSSAF_DECLARATION),
    (DocType.URSSAF_CERTIFICATE, CLASSIFY_URSSAF_CERTIFICATE),
    (DocType.SIRET_CERTIFICATE, CLASSIFY_SIRET_CERTIFICATE),
    (DocType.COMPANY_REGISTRATION, CLASSIFY_COMPANY_REGISTRATION),
    (DocType.PAYMENT, CLASSIFY_PAYMENT),
    (DocType.INVOICE, CLASSIFY_INVOICE),
    (DocType.QUOTE, CLASSIFY_QUOTE),
    (DocType.BANK_ACCOUNT_DETAILS, CLASSIFY_BANK_ACCOUNT_DETAILS),
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
