from __future__ import annotations

import re

_DATE_PATTERN = r"\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2}"


def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _find_all(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, re.IGNORECASE)


def _extract_sirets(text: str) -> dict:
    sirets = _find_all(r"\b(\d{14})\b", text)
    if not sirets:
        return {}
    result = {"siret": sirets[0]}
    if len(sirets) > 1:
        result["siret_client"] = sirets[1]
    return result


def _extract_tva(text: str) -> dict:
    tva = _find(r"\b(FR[A-Z0-9]{2}\d{9})\b", text)
    return {"tva": tva} if tva else {}


def _extract_banking(text: str) -> dict:
    fields = {}
    iban = _find(r"\b(FR\d{2}[\s\d]{20,30})\b", text)
    if iban:
        fields["iban"] = re.sub(r"\s", "", iban)
    bic = _find(r"\bBIC\s*[:\-]?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b", text)
    if bic:
        fields["bic"] = bic
    return fields


def _extract_montants(text: str) -> dict:
    fields = {}
    ht = _find(r"(?:total\s+HT|montant\s+HT|HT)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if ht:
        fields["montant_ht"] = ht.replace(" ", "").replace(",", ".")
    ttc = _find(r"(?:total\s+TTC|montant\s+TTC|TTC)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if ttc:
        fields["montant_ttc"] = ttc.replace(" ", "").replace(",", ".")
    return fields


def _extract_dates(text: str) -> dict:
    fields = {}
    date = _find(rf"(?:date|émission|inscription|le)\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if date:
        fields["date_emission"] = date
    exp = _find(rf"(?:expir(?:ation|e)|validit[eé]|valable jusqu)\S*\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if exp:
        fields["date_expiration"] = exp
    return fields


def extract_fields(text: str) -> dict:
    fields: dict = {}
    fields.update(_extract_sirets(text))
    fields.update(_extract_tva(text))
    fields.update(_extract_banking(text))
    fields.update(_extract_montants(text))
    fields.update(_extract_dates(text))
    return fields
