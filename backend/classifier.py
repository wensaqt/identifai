from __future__ import annotations

import re

DOC_TYPES = [
    "facture",
    "devis",
    "attestation_siret",
    "attestation_urssaf",
    "kbis",
    "rib",
    "payment",
    "urssaf_declaration",
]

# Each rule: list of patterns that ALL must match (AND logic).
# Rules are checked top-to-bottom; first match wins.
# Order matters: more specific rules first.
_RULES: list[tuple[str, list[str]]] = [
    ("urssaf_declaration", [r"urssaf", r"d[ée]claration\s+de\s+chiffre"]),
    ("attestation_urssaf", [r"urssaf", r"attestation"]),
    ("attestation_siret", [r"sirene|siret", r"avis\s+de\s+situation|r[ée]pertoire"]),
    ("kbis", [r"extrait\s*k\s*bis|k\s*bis|greffe|tribunal\s+de\s+commerce"]),
    ("rib", [r"relev[ée]\s+d.identit[ée]\s+bancaire|rib", r"iban"]),
    ("payment", [r"confirmation\s+de\s+paiement"]),
    ("facture", [r"facture"]),
    ("devis", [r"devis"]),
]


def classify_document(text: str) -> str | None:
    """Classify a document based on OCR text using keyword rules.

    Returns a document type string or None if no match.
    """
    text_lower = text.lower()

    for doc_type, patterns in _RULES:
        if all(re.search(p, text_lower) for p in patterns):
            return doc_type

    return None
