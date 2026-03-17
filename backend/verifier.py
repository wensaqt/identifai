from __future__ import annotations

import logging
from datetime import datetime

from consts.doc_types import ATTESTATION_TYPES, INVOICE_TYPES, DocType
from consts.fields import FieldName as F

logger = logging.getLogger(__name__)

_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")
_TVA_TOLERANCE = 0.02
_PAYMENT_TOLERANCE = 0.01
_REVENUE_THRESHOLD = 0.9


class DocumentVerifier:

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _safe_float(value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_field(doc: dict, field: str) -> str | None:
        return doc.get("fields", {}).get(field)

    @staticmethod
    def _get_doc_type(doc: dict) -> str | None:
        return doc.get("doc_type")

    # ── Checks ───────────────────────────────────────────────────────────

    def check_siret_coherence(self, documents: list[dict]) -> list[dict]:
        invoices = [d for d in documents if self._get_doc_type(d) in INVOICE_TYPES]
        attestations = [d for d in documents if self._get_doc_type(d) in ATTESTATION_TYPES]

        if not invoices or not attestations:
            return []

        invoice_sirets = set()
        for d in invoices:
            s = self._get_field(d, F.SIRET_EMETTEUR) or self._get_field(d, F.SIRET)
            if s:
                invoice_sirets.add(s)

        attestation_sirets = {self._get_field(d, F.SIRET) for d in attestations if self._get_field(d, F.SIRET)}

        mismatches = invoice_sirets.symmetric_difference(attestation_sirets)
        if not mismatches:
            return []

        return [{
            "type": "siret_mismatch",
            "severity": "error",
            "message": f"SIRET incohérent entre factures/devis et attestations : {', '.join(mismatches)}",
            "files": [
                d["filename"] for d in documents
                if (self._get_field(d, F.SIRET) in mismatches
                    or self._get_field(d, F.SIRET_EMETTEUR) in mismatches)
            ],
        }]

    def check_expired_attestations(self, documents: list[dict]) -> list[dict]:
        issues = []
        today = datetime.today()

        for doc in documents:
            if self._get_doc_type(doc) not in (DocType.ATTESTATION_URSSAF, DocType.ATTESTATION_SIRET):
                continue
            exp_str = self._get_field(doc, F.DATE_EXPIRATION)
            if not exp_str:
                continue
            exp_date = self._parse_date(exp_str)
            if exp_date and exp_date < today:
                issues.append({
                    "type": "expired_attestation",
                    "severity": "error",
                    "message": f"Attestation expirée depuis le {exp_str}",
                    "files": [doc["filename"]],
                })
        return issues

    def check_tva_coherence(self, documents: list[dict]) -> list[dict]:
        issues = []

        for doc in documents:
            if self._get_doc_type(doc) not in (DocType.FACTURE, DocType.INVOICE):
                continue
            ht = self._safe_float(self._get_field(doc, F.MONTANT_HT))
            tva = self._safe_float(self._get_field(doc, F.MONTANT_TVA))
            rate = self._safe_float(self._get_field(doc, F.TVA_RATE))

            if ht is None or tva is None or rate is None:
                continue

            expected = round(ht * rate, 2)
            if abs(tva - expected) > _TVA_TOLERANCE:
                issues.append({
                    "type": "tva_mismatch",
                    "severity": "warning",
                    "message": f"TVA incohérente : {tva} vs attendu {expected} (HT={ht}, taux={rate})",
                    "files": [doc["filename"]],
                })
        return issues

    def check_payment_amount(self, documents: list[dict]) -> list[dict]:
        issues = []

        invoices = {
            self._get_field(d, F.INVOICE_ID): d
            for d in documents
            if self._get_doc_type(d) in (DocType.FACTURE, DocType.INVOICE) and self._get_field(d, F.INVOICE_ID)
        }

        for doc in documents:
            if self._get_doc_type(doc) != DocType.PAYMENT:
                continue
            ref = self._get_field(doc, F.REFERENCE_FACTURE)
            if not ref or ref not in invoices:
                continue

            pay_amount = self._safe_float(self._get_field(doc, F.MONTANT))
            inv_ttc = self._safe_float(self._get_field(invoices[ref], F.MONTANT_TTC))

            if pay_amount is not None and inv_ttc is not None and abs(pay_amount - inv_ttc) > _PAYMENT_TOLERANCE:
                issues.append({
                    "type": "payment_amount_mismatch",
                    "severity": "error",
                    "message": f"Paiement {pay_amount} != facture TTC {inv_ttc} (réf {ref})",
                    "files": [doc["filename"], invoices[ref]["filename"]],
                })
        return issues

    def check_orphan_payments(self, documents: list[dict]) -> list[dict]:
        issues = []

        invoice_ids = {
            self._get_field(d, F.INVOICE_ID)
            for d in documents
            if self._get_doc_type(d) in (DocType.FACTURE, DocType.INVOICE) and self._get_field(d, F.INVOICE_ID)
        }

        for doc in documents:
            if self._get_doc_type(doc) != DocType.PAYMENT:
                continue
            ref = self._get_field(doc, F.REFERENCE_FACTURE)
            if ref and ref not in invoice_ids:
                issues.append({
                    "type": "orphan_payment",
                    "severity": "warning",
                    "message": f"Paiement référence une facture inexistante : {ref}",
                    "files": [doc["filename"]],
                })
        return issues

    def check_declared_revenue(self, documents: list[dict]) -> list[dict]:
        issues = []

        total_ht = 0.0
        for doc in documents:
            if self._get_doc_type(doc) not in (DocType.FACTURE, DocType.INVOICE):
                continue
            ht = self._safe_float(self._get_field(doc, F.MONTANT_HT))
            if ht:
                total_ht += ht

        if total_ht == 0:
            return issues

        for doc in documents:
            if self._get_doc_type(doc) != DocType.URSSAF_DECLARATION:
                continue
            declared = self._safe_float(self._get_field(doc, F.CHIFFRE_AFFAIRES_DECLARE))
            if declared is not None and declared < total_ht * _REVENUE_THRESHOLD:
                issues.append({
                    "type": "undeclared_revenue",
                    "severity": "warning",
                    "message": f"CA déclaré ({declared}) inférieur à 90% du HT facturé ({total_ht})",
                    "files": [doc["filename"]],
                })
        return issues

    # ── Public API ───────────────────────────────────────────────────────

    def verify(self, documents: list[dict]) -> list[dict]:
        issues = []
        issues.extend(self.check_siret_coherence(documents))
        issues.extend(self.check_expired_attestations(documents))
        issues.extend(self.check_tva_coherence(documents))
        issues.extend(self.check_payment_amount(documents))
        issues.extend(self.check_orphan_payments(documents))
        issues.extend(self.check_declared_revenue(documents))
        logger.info("[VERIFY] %d documents analysés, %d anomalies détectées", len(documents), len(issues))
        return issues


_verifier = DocumentVerifier()


def verify_documents(documents: list[dict]) -> list[dict]:
    return _verifier.verify(documents)
