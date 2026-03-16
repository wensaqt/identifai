from __future__ import annotations

import re


def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _find_all(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, re.IGNORECASE)


def extract_fields(text: str) -> dict:
    fields: dict = {}

    # SIRET — 14 chiffres
    sirets = _find_all(r"\b(\d{14})\b", text)
    if sirets:
        fields["siret"] = sirets[0]
        if len(sirets) > 1:
            fields["siret_client"] = sirets[1]

    # TVA intracommunautaire — FR + 2 chars + 9 chiffres
    tva = _find(r"\b(FR[A-Z0-9]{2}\d{9})\b", text)
    if tva:
        fields["tva"] = tva

    # IBAN — FR76 suivi de chiffres/lettres
    iban = _find(r"\b(FR\d{2}[\s\d]{20,30})\b", text)
    if iban:
        fields["iban"] = re.sub(r"\s", "", iban)

    # BIC — 8 ou 11 caractères alphanumériques
    bic = _find(r"\bBIC\s*[:\-]?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b", text)
    if bic:
        fields["bic"] = bic

    # Montant HT
    ht = _find(r"(?:total\s+HT|montant\s+HT|HT)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if ht:
        fields["montant_ht"] = ht.replace(" ", "").replace(",", ".")

    # Montant TTC
    ttc = _find(r"(?:total\s+TTC|montant\s+TTC|TTC)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if ttc:
        fields["montant_ttc"] = ttc.replace(" ", "").replace(",", ".")

    # Date d'émission — formats DD/MM/YYYY ou DD-MM-YYYY
    date = _find(r"(?:date|émission|le)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text)
    if date:
        fields["date_emission"] = date

    # Date d'expiration
    exp = _find(r"(?:expir(?:ation|e)|validit[eé]|valable jusqu)\S*\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text)
    if exp:
        fields["date_expiration"] = exp

    return fields
