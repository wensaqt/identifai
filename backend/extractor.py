from __future__ import annotations

import re

_DATE_PATTERN = r"\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2}"


def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _find_all(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, re.IGNORECASE)


# ── Generic extractors ───────────────────────────────────────────────────────

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
    tva = _find(r"TVA\s+\d+%?\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if tva:
        fields["montant_tva"] = tva.replace(" ", "").replace(",", ".")
    return fields


def _extract_dates(text: str) -> dict:
    fields = {}
    date = _find(rf"(?:date|[ée]mission|inscription|le)\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if date:
        fields["date_emission"] = date
    exp = _find(rf"(?:expir(?:ation|e)|validit[eé]|valable jusqu)\S*\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if exp:
        fields["date_expiration"] = exp
    delivrance = _find(rf"(?:d[ée]livrance)\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if delivrance:
        fields["date_delivrance"] = delivrance
    prestation = _find(rf"(?:prestation)\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if prestation:
        fields["date_prestation"] = prestation
    return fields


# ── Type-specific extractors ─────────────────────────────────────────────────

def _extract_payment_fields(text: str) -> dict:
    fields = {}
    pid = _find(r"\b(PAY-\d{4}-\d{4})\b", text)
    if pid:
        fields["payment_id"] = pid
    ref = _find(r"[Rr][ée]f\.?\s*facture\s*[:\-]?\s*(F-\d{4}-\d{4})", text)
    if ref:
        fields["reference_facture"] = ref
    montant = _find(r"[Mm]ontant\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?", text)
    if montant:
        fields["montant"] = montant.replace(" ", "").replace(",", ".")
    date = _find(rf"[Dd]ate\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if date:
        fields["date_paiement"] = date
    methode = _find(r"[Mm][ée]thode\s*[:\-]?\s*(virement|pr[ée]l[èe]vement|ch[èe]que|carte\s+bancaire)", text)
    if methode:
        fields["methode"] = methode.strip()
    return fields


def _extract_declaration_fields(text: str) -> dict:
    fields = {}
    periode = _find(r"\b(\d{4}-T[1-4])\b", text)
    if periode:
        fields["periode"] = periode
    ca = _find(r"[Cc]hiffre\s+d.affaires\s+d[ée]clar[ée]\s*[:\-]?\s*([\d\s,.]+)\s*[€E]?", text)
    if ca:
        fields["chiffre_affaires_declare"] = ca.replace(" ", "").replace(",", ".")
    date = _find(rf"[Dd]ate\s+de\s+d[ée]claration\s*[:\-]?\s*({_DATE_PATTERN})", text)
    if date:
        fields["date_declaration"] = date
    sirets = _find_all(r"\b(\d{14})\b", text)
    if sirets:
        fields["siret"] = sirets[0]
    return fields


# ── Field remapping per doc type ─────────────────────────────────────────────

_SIRET_REMAP_TYPES = {"facture", "invoice", "devis"}


def _remap_fields(fields: dict, doc_type: str) -> dict:
    """Rename generic field names to type-specific names."""
    if doc_type in _SIRET_REMAP_TYPES and "siret" in fields:
        fields["siret_emetteur"] = fields.pop("siret")
    return fields


# ── Type-aware extraction dispatch ───────────────────────────────────────────

_TYPE_EXTRACTORS: dict[str, list] = {
    "facture": [_extract_sirets, _extract_tva, _extract_montants, _extract_dates],
    "invoice": [_extract_sirets, _extract_tva, _extract_montants, _extract_dates],
    "devis": [_extract_sirets, _extract_tva, _extract_montants, _extract_dates],
    "attestation_siret": [_extract_sirets, _extract_dates],
    "attestation_urssaf": [_extract_sirets, _extract_dates],
    "kbis": [_extract_sirets, _extract_dates],
    "rib": [_extract_banking],
    "payment": [_extract_payment_fields],
    "urssaf_declaration": [_extract_declaration_fields],
}

# All extractors for backward compatibility (when doc_type is None)
_ALL_EXTRACTORS = [
    _extract_sirets, _extract_tva, _extract_banking,
    _extract_montants, _extract_dates,
]


def extract_fields(text: str, doc_type: str | None = None) -> dict:
    extractors = _TYPE_EXTRACTORS.get(doc_type, _ALL_EXTRACTORS) if doc_type else _ALL_EXTRACTORS
    fields: dict = {}
    for extractor in extractors:
        fields.update(extractor(text))
    if doc_type:
        fields = _remap_fields(fields, doc_type)
    return fields
