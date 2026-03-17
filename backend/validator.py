from __future__ import annotations

import logging
import re

from consts.fields import FieldName as F
from consts.patterns import (
    VALIDATE_AMOUNT,
    VALIDATE_BIC,
    VALIDATE_DATE,
    VALIDATE_DATE_ISO,
    VALIDATE_IBAN,
    VALIDATE_PERIODE,
    VALIDATE_SIREN,
    VALIDATE_SIRET,
    VALIDATE_TVA,
)
from models import DOC_TYPE_MODELS

logger = logging.getLogger(__name__)

FORMAT_RULES: dict[str, str] = {
    F.SIRET: VALIDATE_SIRET,
    F.SIRET_EMETTEUR: VALIDATE_SIRET,
    F.SIRET_CLIENT: VALIDATE_SIRET,
    F.SIREN: VALIDATE_SIREN,
    F.TVA: VALIDATE_TVA,
    F.IBAN: VALIDATE_IBAN,
    F.BIC: VALIDATE_BIC,
    F.MONTANT_HT: VALIDATE_AMOUNT,
    F.MONTANT_TTC: VALIDATE_AMOUNT,
    F.MONTANT_TVA: VALIDATE_AMOUNT,
    F.MONTANT: VALIDATE_AMOUNT,
    F.CHIFFRE_AFFAIRES_DECLARE: VALIDATE_AMOUNT,
    F.DATE_EMISSION: VALIDATE_DATE,
    F.DATE_EXPIRATION: VALIDATE_DATE,
    F.DATE_PAIEMENT: VALIDATE_DATE,
    F.DATE_VALIDITE: VALIDATE_DATE,
    F.DATE_DECLARATION: VALIDATE_DATE,
    F.DATE_DELIVRANCE: VALIDATE_DATE,
    F.DATE_INSCRIPTION: VALIDATE_DATE_ISO,
    F.PERIODE: VALIDATE_PERIODE,
}


class DocumentValidator:

    def check_completeness(self, doc_type: str | None, fields: dict) -> list[dict]:
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

    def check_format(self, fields: dict) -> list[dict]:
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

    def validate(self, doc_type: str | None, fields: dict) -> dict:
        completeness = self.check_completeness(doc_type, fields)
        fmt = self.check_format(fields)
        is_valid = len(completeness) == 0 and len(fmt) == 0
        logger.info("[VALIDATE] doc_type=%s is_valid=%s (missing=%d, format=%d)",
                     doc_type, is_valid, len(completeness), len(fmt))
        return {
            "completeness": completeness,
            "format": fmt,
            "is_valid": is_valid,
        }


_validator = DocumentValidator()


def validate_completeness(doc_type: str | None, fields: dict) -> list[dict]:
    return _validator.check_completeness(doc_type, fields)


def validate_format(fields: dict) -> list[dict]:
    return _validator.check_format(fields)


def validate_document(doc_type: str | None, fields: dict) -> dict:
    return _validator.validate(doc_type, fields)
