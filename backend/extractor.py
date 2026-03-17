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

    def _find_amount(self, pattern: str, text: str) -> str | None:
        raw = self._find(pattern, text)
        return self._clean_amount(raw) if raw else None

    # ── Single-field getters ─────────────────────────────────────────────

    def get_invoice_id(self, text: str) -> dict:
        iid = self._find(EXTRACT_INVOICE_ID, text)
        return {F.INVOICE_ID: iid} if iid else {}

    def get_siret(self, text: str) -> dict:
        sirets = self._find_all(EXTRACT_SIRET, text)
        if not sirets:
            return {}
        result = {F.SIRET: sirets[0]}
        if len(sirets) > 1:
            result[F.SIRET_CLIENT] = sirets[1]
        return result

    def get_tva(self, text: str) -> dict:
        tva = self._find(EXTRACT_TVA, text)
        return {F.TVA: tva} if tva else {}

    def get_iban(self, text: str) -> dict:
        iban = self._find(EXTRACT_IBAN, text)
        if not iban:
            return {}
        return {F.IBAN: re.sub(r"\s", "", iban)}

    def get_bic(self, text: str) -> dict:
        bic = self._find(EXTRACT_BIC, text)
        return {F.BIC: bic} if bic else {}

    def get_montant_ht(self, text: str) -> dict:
        val = self._find_amount(EXTRACT_MONTANT_HT, text)
        return {F.MONTANT_HT: val} if val else {}

    def get_montant_ttc(self, text: str) -> dict:
        val = self._find_amount(EXTRACT_MONTANT_TTC, text)
        return {F.MONTANT_TTC: val} if val else {}

    def get_montant_tva(self, text: str) -> dict:
        val = self._find_amount(EXTRACT_MONTANT_TVA, text)
        return {F.MONTANT_TVA: val} if val else {}

    def get_montant(self, text: str) -> dict:
        val = self._find_amount(EXTRACT_MONTANT, text)
        return {F.MONTANT: val} if val else {}

    def get_date_emission(self, text: str) -> dict:
        d = self._find(rf"(?:date|[ée]mission|inscription|le)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        return {F.DATE_EMISSION: d} if d else {}

    def get_date_expiration(self, text: str) -> dict:
        d = self._find(rf"(?:expir(?:ation|e)|validit[eé]|valable jusqu)\S*\s*[:\-]?\s*({EXTRACT_DATE})", text)
        return {F.DATE_EXPIRATION: d} if d else {}

    def get_date_delivrance(self, text: str) -> dict:
        d = self._find(rf"(?:d[ée]livrance)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        return {F.DATE_DELIVRANCE: d} if d else {}

    def get_date_prestation(self, text: str) -> dict:
        d = self._find(rf"(?:prestation)\s*[:\-]?\s*({EXTRACT_DATE})", text)
        return {F.DATE_PRESTATION: d} if d else {}

    def get_date_paiement(self, text: str) -> dict:
        d = self._find(rf"[Dd]ate\s*[:\-]?\s*({EXTRACT_DATE})", text)
        return {F.DATE_PAIEMENT: d} if d else {}

    def get_date_declaration(self, text: str) -> dict:
        d = self._find(EXTRACT_DATE_DECLARATION, text)
        return {F.DATE_DECLARATION: d} if d else {}

    def get_payment_id(self, text: str) -> dict:
        pid = self._find(EXTRACT_PAYMENT_ID, text)
        return {F.PAYMENT_ID: pid} if pid else {}

    def get_reference_facture(self, text: str) -> dict:
        ref = self._find(EXTRACT_REFERENCE_FACTURE, text)
        return {F.REFERENCE_FACTURE: ref} if ref else {}

    def get_methode(self, text: str) -> dict:
        m = self._find(EXTRACT_METHODE, text)
        return {F.METHODE: m.strip()} if m else {}

    def get_periode(self, text: str) -> dict:
        p = self._find(EXTRACT_PERIODE, text)
        return {F.PERIODE: p} if p else {}

    def get_chiffre_affaires(self, text: str) -> dict:
        val = self._find_amount(EXTRACT_CA_DECLARE, text)
        return {F.CHIFFRE_AFFAIRES_DECLARE: val} if val else {}

    # ── Remapping ────────────────────────────────────────────────────────

    _SIRET_REMAP_TYPES = {DocType.FACTURE, DocType.INVOICE, DocType.DEVIS}

    def _remap_fields(self, fields: dict, doc_type: str) -> dict:
        if doc_type in self._SIRET_REMAP_TYPES and F.SIRET in fields:
            fields[F.SIRET_EMETTEUR] = fields.pop(F.SIRET)
        return fields

    # ── Dispatch ─────────────────────────────────────────────────────────

    _TYPE_EXTRACTORS = None

    def _get_type_map(self) -> dict:
        if self._TYPE_EXTRACTORS is None:
            self._TYPE_EXTRACTORS = {
                DocType.FACTURE: self._invoice_extractors(),
                DocType.INVOICE: self._invoice_extractors(),
                DocType.DEVIS: self._devis_extractors(),
                DocType.ATTESTATION_SIRET: [self.get_siret, self.get_date_emission],
                DocType.ATTESTATION_URSSAF: [self.get_siret, self.get_date_expiration, self.get_date_delivrance],
                DocType.KBIS: [self.get_siret, self.get_date_emission],
                DocType.RIB: [self.get_iban, self.get_bic],
                DocType.PAYMENT: self._payment_extractors(),
                DocType.URSSAF_DECLARATION: self._declaration_extractors(),
            }
        return self._TYPE_EXTRACTORS

    def _invoice_extractors(self):
        return [
            self.get_invoice_id, self.get_siret, self.get_tva,
            self.get_montant_ht, self.get_montant_ttc, self.get_montant_tva,
            self.get_date_emission, self.get_date_prestation,
        ]

    def _devis_extractors(self):
        return [
            self.get_siret, self.get_tva,
            self.get_montant_ht, self.get_montant_ttc,
            self.get_date_emission, self.get_date_expiration,
        ]

    def _payment_extractors(self):
        return [
            self.get_payment_id, self.get_reference_facture,
            self.get_montant, self.get_date_paiement, self.get_methode,
        ]

    def _declaration_extractors(self):
        return [
            self.get_siret, self.get_periode,
            self.get_chiffre_affaires, self.get_date_declaration,
        ]

    def _fallback_extractors(self):
        return [
            self.get_siret, self.get_tva, self.get_iban, self.get_bic,
            self.get_montant_ht, self.get_montant_ttc,
            self.get_date_emission, self.get_date_expiration,
        ]

    def _get_extractors(self, doc_type: str | None):
        if not doc_type:
            return self._fallback_extractors()
        return self._get_type_map().get(doc_type, self._fallback_extractors())

    def extract(self, text: str, doc_type: str | None = None) -> dict:
        fields: dict = {}
        for extractor in self._get_extractors(doc_type):
            fields.update(extractor(text))
        if doc_type:
            fields = self._remap_fields(fields, doc_type)
        logger.info("[EXTRACT] %d champs extraits (doc_type=%s)", len(fields), doc_type)
        return fields


_extractor = FieldExtractor()


def extract_fields(text: str, doc_type: str | None = None) -> dict:
    return _extractor.extract(text, doc_type)
