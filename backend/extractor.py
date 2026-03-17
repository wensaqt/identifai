from __future__ import annotations

import logging
import re

from consts.doc_types import DocType
from consts.fields import FieldName as F
from consts.patterns import (
    EXTRACT_BIC,
    EXTRACT_CA_DECLARE,
    EXTRACT_DATE,
    EXTRACT_DATE_DECLARATION,
    EXTRACT_IBAN,
    EXTRACT_INVOICE_ID,
    EXTRACT_METHODE,
    EXTRACT_MONTANT,
    EXTRACT_MONTANT_HT,
    EXTRACT_MONTANT_TTC,
    EXTRACT_MONTANT_TVA,
    EXTRACT_PAYMENT_ID,
    EXTRACT_PERIODE,
    EXTRACT_REFERENCE_FACTURE,
    EXTRACT_SIRET,
    EXTRACT_TVA,
)

logger = logging.getLogger(__name__)


class FieldExtractor:

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _find(pattern: str, text: str) -> str | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _find_all(pattern: str, text: str) -> list[str]:
        return re.findall(pattern, text, re.IGNORECASE)

    @staticmethod
    def _clean_amount(raw: str) -> str:
        return raw.replace(" ", "").replace(",", ".")

    # ── Generic extractors ───────────────────────────────────────────────

    def get_sirets(self, text: str) -> dict:
        sirets = self._find_all(EXTRACT_SIRET, text)
        if not sirets:
            return {}
        result = {F.SIRET: sirets[0]}
        if len(sirets) > 1:
            result[F.SIRET_CLIENT] = sirets[1]
        return result

    def get_invoice_id(self, text: str) -> dict:
        iid = self._find(EXTRACT_INVOICE_ID, text)
        return {F.INVOICE_ID: iid} if iid else {}

    def get_tva(self, text: str) -> dict:
        tva = self._find(EXTRACT_TVA, text)
        return {F.TVA: tva} if tva else {}

    def get_banking(self, text: str) -> dict:
        fields = {}
        iban = self._find(EXTRACT_IBAN, text)
        if iban:
            fields[F.IBAN] = re.sub(r"\s", "", iban)
        bic = self._find(EXTRACT_BIC, text)
        if bic:
            fields[F.BIC] = bic
        return fields

    def get_montants(self, text: str) -> dict:
        fields = {}
        ht = self._find(EXTRACT_MONTANT_HT, text)
        if ht:
            fields[F.MONTANT_HT] = self._clean_amount(ht)
        ttc = self._find(EXTRACT_MONTANT_TTC, text)
        if ttc:
            fields[F.MONTANT_TTC] = self._clean_amount(ttc)
        tva = self._find(EXTRACT_MONTANT_TVA, text)
        if tva:
            fields[F.MONTANT_TVA] = self._clean_amount(tva)
        return fields

    def get_dates(self, text: str) -> dict:
        fields = {}
        date = self._find(rf"(?:date|[ée]mission|inscription|le)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        if date:
            fields[F.DATE_EMISSION] = date
        exp = self._find(rf"(?:expir(?:ation|e)|validit[eé]|valable jusqu)\S*\s*[:\-]?\s*({EXTRACT_DATE})", text)
        if exp:
            fields[F.DATE_EXPIRATION] = exp
        delivrance = self._find(rf"(?:d[ée]livrance)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        if delivrance:
            fields[F.DATE_DELIVRANCE] = delivrance
        prestation = self._find(rf"(?:prestation)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        if prestation:
            fields[F.DATE_PRESTATION] = prestation
        return fields

    # ── Type-specific extractors ─────────────────────────────────────────

    def get_payment_fields(self, text: str) -> dict:
        fields = {}
        pid = self._find(EXTRACT_PAYMENT_ID, text)
        if pid:
            fields[F.PAYMENT_ID] = pid
        ref = self._find(EXTRACT_REFERENCE_FACTURE, text)
        if ref:
            fields[F.REFERENCE_FACTURE] = ref
        montant = self._find(EXTRACT_MONTANT, text)
        if montant:
            fields[F.MONTANT] = self._clean_amount(montant)
        date = self._find(rf"[Dd]ate\s*[:\-]?\s*({EXTRACT_DATE})", text)
        if date:
            fields[F.DATE_PAIEMENT] = date
        methode = self._find(EXTRACT_METHODE, text)
        if methode:
            fields[F.METHODE] = methode.strip()
        return fields

    def get_declaration_fields(self, text: str) -> dict:
        fields = {}
        periode = self._find(EXTRACT_PERIODE, text)
        if periode:
            fields[F.PERIODE] = periode
        ca = self._find(EXTRACT_CA_DECLARE, text)
        if ca:
            fields[F.CHIFFRE_AFFAIRES_DECLARE] = self._clean_amount(ca)
        date = self._find(EXTRACT_DATE_DECLARATION, text)
        if date:
            fields[F.DATE_DECLARATION] = date
        sirets = self._find_all(EXTRACT_SIRET, text)
        if sirets:
            fields[F.SIRET] = sirets[0]
        return fields

    # ── Remapping ────────────────────────────────────────────────────────

    _SIRET_REMAP_TYPES = {DocType.FACTURE, DocType.INVOICE, DocType.DEVIS}

    def _remap_fields(self, fields: dict, doc_type: str) -> dict:
        if doc_type in self._SIRET_REMAP_TYPES and F.SIRET in fields:
            fields[F.SIRET_EMETTEUR] = fields.pop(F.SIRET)
        return fields

    # ── Dispatch ─────────────────────────────────────────────────────────

    def _get_extractors(self, doc_type: str | None):
        type_map = {
            DocType.FACTURE: [self.get_invoice_id, self.get_sirets, self.get_tva, self.get_montants, self.get_dates],
            DocType.INVOICE: [self.get_invoice_id, self.get_sirets, self.get_tva, self.get_montants, self.get_dates],
            DocType.DEVIS: [self.get_sirets, self.get_tva, self.get_montants, self.get_dates],
            DocType.ATTESTATION_SIRET: [self.get_sirets, self.get_dates],
            DocType.ATTESTATION_URSSAF: [self.get_sirets, self.get_dates],
            DocType.KBIS: [self.get_sirets, self.get_dates],
            DocType.RIB: [self.get_banking],
            DocType.PAYMENT: [self.get_payment_fields],
            DocType.URSSAF_DECLARATION: [self.get_declaration_fields],
        }
        all_extractors = [
            self.get_sirets, self.get_tva, self.get_banking,
            self.get_montants, self.get_dates,
        ]
        if doc_type:
            return type_map.get(doc_type, all_extractors)
        return all_extractors

    def extract(self, text: str, doc_type: str | None = None) -> dict:
        extractors = self._get_extractors(doc_type)
        fields: dict = {}
        for extractor in extractors:
            fields.update(extractor(text))
        if doc_type:
            fields = self._remap_fields(fields, doc_type)
        logger.info("[EXTRACT] %d champs extraits (doc_type=%s)", len(fields), doc_type)
        return fields


_extractor = FieldExtractor()


def extract_fields(text: str, doc_type: str | None = None) -> dict:
    return _extractor.extract(text, doc_type)
