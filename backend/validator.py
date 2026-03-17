from __future__ import annotations

import re

from models import DOC_TYPE_MODELS

# ── Format rules ─────────────────────────────────────────────────────────────

_DATE_RE = r"^\d{2}/\d{2}/\d{4}$|^\d{4}-\d{2}-\d{2}$"
_AMOUNT_RE = r"^\d+(\.\d{1,2})?$"

FORMAT_RULES: dict[str, str] = {
    "siret": r"^\d{14}$",
    "siret_emetteur": r"^\d{14}$",
    "siret_client": r"^\d{14}$",
    "siren": r"^\d{9}$",
    "tva": r"^FR[A-Z0-9]{2}\d{9}$",
    "iban": r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$",
    "bic": r"^[A-Z]{6}[A-Z0-9]{2,5}$",
    "montant_ht": _AMOUNT_RE,
    "montant_ttc": _AMOUNT_RE,
    "montant_tva": _AMOUNT_RE,
    "montant": _AMOUNT_RE,
    "chiffre_affaires_declare": _AMOUNT_RE,
    "date_emission": _DATE_RE,
    "date_expiration": _DATE_RE,
    "date_paiement": _DATE_RE,
    "date_validite": _DATE_RE,
    "date_declaration": _DATE_RE,
    "date_delivrance": _DATE_RE,
    "date_inscription": r"^\d{4}-\d{2}-\d{2}$",
    "periode": r"^\d{4}-T[1-4]$",
}


# ── Layer 1: completeness ────────────────────────────────────────────────────

def validate_completeness(doc_type: str | None, fields: dict) -> list[dict]:
    if not doc_type or doc_type not in DOC_TYPE_MODELS:
        return []
    model_cls = DOC_TYPE_MODELS[doc_type]
    issues = []
    for field_name in model_cls.REQUIRED_FIELDS:
        if not fields.get(field_name):
            issues.append({
                "type": "missing_field",
                "severity": "warning",
                "field": field_name,
                "message": f"Champ requis manquant : {field_name}",
            })
    return issues


# ── Layer 2: format ──────────────────────────────────────────────────────────

def validate_format(fields: dict) -> list[dict]:
    issues = []
    for field_name, value in fields.items():
        if field_name not in FORMAT_RULES or value is None:
            continue
        pattern = FORMAT_RULES[field_name]
        if not re.match(pattern, str(value)):
            issues.append({
                "type": "invalid_format",
                "severity": "warning",
                "field": field_name,
                "value": str(value),
                "message": f"Format invalide pour {field_name}",
            })
    return issues


# ── Public API ───────────────────────────────────────────────────────────────

def validate_document(doc_type: str | None, fields: dict) -> dict:
    completeness = validate_completeness(doc_type, fields)
    fmt = validate_format(fields)
    return {
        "completeness": completeness,
        "format": fmt,
        "is_valid": len(completeness) == 0 and len(fmt) == 0,
    }
