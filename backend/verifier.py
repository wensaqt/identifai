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


# ── Issue builders ───────────────────────────────────────────────────────────

def _issue(issue_type: str, severity: str, message: str, files: list[str]) -> dict:
    return {"type": issue_type, "severity": severity, "message": message, "files": files}


def _error(issue_type: str, message: str, files: list[str]) -> dict:
    return _issue(issue_type, "error", message, files)


def _warning(issue_type: str, message: str, files: list[str]) -> dict:
    return _issue(issue_type, "warning", message, files)


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

    # ── Filters ──────────────────────────────────────────────────────────

    def _get_invoices(self, documents: list[dict]) -> list[dict]:
        return [d for d in documents if self._get_doc_type(d) in INVOICE_TYPES]

    def _get_attestations(self, documents: list[dict]) -> list[dict]:
        return [d for d in documents if self._get_doc_type(d) in ATTESTATION_TYPES]

    def _get_payments(self, documents: list[dict]) -> list[dict]:
        return [d for d in documents if self._get_doc_type(d) == DocType.PAYMENT]

    def _get_declarations(self, documents: list[dict]) -> list[dict]:
        return [d for d in documents if self._get_doc_type(d) == DocType.URSSAF_DECLARATION]

    def _get_invoice_siret(self, doc: dict) -> str | None:
        return self._get_field(doc, F.SIRET_EMETTEUR) or self._get_field(doc, F.SIRET)

    def _build_invoice_index(self, documents: list[dict]) -> dict[str, dict]:
        invoices = self._get_invoices(documents)
        return {
            self._get_field(d, F.INVOICE_ID): d
            for d in invoices
            if self._get_field(d, F.INVOICE_ID)
        }

    def _get_invoice_ids(self, documents: list[dict]) -> set[str]:
        return set(self._build_invoice_index(documents).keys())

    def _sum_invoiced_ht(self, documents: list[dict]) -> float:
        total = 0.0
        for doc in self._get_invoices(documents):
            ht = self._safe_float(self._get_field(doc, F.MONTANT_HT))
            if ht:
                total += ht
        return total

    # ── Checks ───────────────────────────────────────────────────────────

    def check_siret_coherence(self, documents: list[dict]) -> list[dict]:
        invoices = self._get_invoices(documents)
        attestations = self._get_attestations(documents)
        if not invoices or not attestations:
            return []

        invoice_sirets = {self._get_invoice_siret(d) for d in invoices if self._get_invoice_siret(d)}
        attestation_sirets = {self._get_field(d, F.SIRET) for d in attestations if self._get_field(d, F.SIRET)}
        mismatches = invoice_sirets.symmetric_difference(attestation_sirets)
        if not mismatches:
            return []

        files = self._files_with_siret(documents, mismatches)
        return [_error("siret_mismatch",
                       f"SIRET incohérent entre factures/devis et attestations : {', '.join(mismatches)}",
                       files)]

    def _files_with_siret(self, documents: list[dict], sirets: set[str]) -> list[str]:
        result = []
        for d in documents:
            s = self._get_field(d, F.SIRET) or self._get_field(d, F.SIRET_EMETTEUR)
            if s in sirets:
                result.append(d["filename"])
        return result

    def check_expired_attestations(self, documents: list[dict]) -> list[dict]:
        today = datetime.today()
        issues = []
        for doc in self._get_attestations(documents):
            issue = self._check_single_expiration(doc, today)
            if issue:
                issues.append(issue)
        return issues

    def _check_single_expiration(self, doc: dict, today: datetime) -> dict | None:
        exp_str = self._get_field(doc, F.DATE_EXPIRATION)
        if not exp_str:
            return None
        exp_date = self._parse_date(exp_str)
        if not exp_date or exp_date >= today:
            return None
        return _error("expired_attestation",
                      f"Attestation expirée depuis le {exp_str}",
                      [doc["filename"]])

    def check_tva_coherence(self, documents: list[dict]) -> list[dict]:
        issues = []
        for doc in self._get_invoices(documents):
            issue = self._check_single_tva(doc)
            if issue:
                issues.append(issue)
        return issues

    def _check_single_tva(self, doc: dict) -> dict | None:
        ht = self._safe_float(self._get_field(doc, F.MONTANT_HT))
        tva = self._safe_float(self._get_field(doc, F.MONTANT_TVA))
        rate = self._safe_float(self._get_field(doc, F.TVA_RATE))
        if ht is None or tva is None or rate is None:
            return None
        expected = round(ht * rate, 2)
        if abs(tva - expected) <= _TVA_TOLERANCE:
            return None
        return _warning("tva_mismatch",
                        f"TVA incohérente : {tva} vs attendu {expected} (HT={ht}, taux={rate})",
                        [doc["filename"]])

    def check_payment_amount(self, documents: list[dict]) -> list[dict]:
        invoice_index = self._build_invoice_index(documents)
        issues = []
        for doc in self._get_payments(documents):
            issue = self._check_single_payment_amount(doc, invoice_index)
            if issue:
                issues.append(issue)
        return issues

    def _check_single_payment_amount(self, doc: dict, invoice_index: dict) -> dict | None:
        ref = self._get_field(doc, F.REFERENCE_FACTURE)
        if not ref or ref not in invoice_index:
            return None
        pay = self._safe_float(self._get_field(doc, F.MONTANT))
        ttc = self._safe_float(self._get_field(invoice_index[ref], F.MONTANT_TTC))
        if pay is None or ttc is None:
            return None
        if abs(pay - ttc) <= _PAYMENT_TOLERANCE:
            return None
        return _error("payment_amount_mismatch",
                      f"Paiement {pay} != facture TTC {ttc} (réf {ref})",
                      [doc["filename"], invoice_index[ref]["filename"]])

    def check_orphan_payments(self, documents: list[dict]) -> list[dict]:
        invoice_ids = self._get_invoice_ids(documents)
        issues = []
        for doc in self._get_payments(documents):
            ref = self._get_field(doc, F.REFERENCE_FACTURE)
            if ref and ref not in invoice_ids:
                issues.append(_warning("orphan_payment",
                                       f"Paiement référence une facture inexistante : {ref}",
                                       [doc["filename"]]))
        return issues

    def check_missing_payment(self, documents: list[dict]) -> list[dict]:
        payment_refs = set()
        for doc in self._get_payments(documents):
            ref = self._get_field(doc, F.REFERENCE_FACTURE)
            if ref:
                payment_refs.add(ref)

        issues = []
        for doc in self._get_invoices(documents):
            statut = self._get_field(doc, F.STATUT_PAIEMENT)
            if statut and statut.lower() == "unpaid":
                continue
            invoice_id = self._get_field(doc, F.INVOICE_ID)
            if not invoice_id:
                continue
            if invoice_id not in payment_refs:
                issues.append(_warning("missing_payment",
                                       f"Aucun paiement trouvé pour la facture {invoice_id}",
                                       [doc["filename"]]))
        return issues

    def check_declared_revenue(self, documents: list[dict]) -> list[dict]:
        total_ht = self._sum_invoiced_ht(documents)
        if total_ht == 0:
            return []
        issues = []
        for doc in self._get_declarations(documents):
            declared = self._safe_float(self._get_field(doc, F.CHIFFRE_AFFAIRES_DECLARE))
            if declared is not None and declared < total_ht * _REVENUE_THRESHOLD:
                issues.append(_warning("undeclared_revenue",
                                       f"CA déclaré ({declared}) inférieur à 90% du HT facturé ({total_ht})",
                                       [doc["filename"]]))
        return issues

    # ── Public API ───────────────────────────────────────────────────────

    def verify(self, documents: list[dict]) -> list[dict]:
        checks = [
            self.check_siret_coherence,
            self.check_expired_attestations,
            self.check_tva_coherence,
            self.check_payment_amount,
            self.check_orphan_payments,
            self.check_missing_payment,
            self.check_declared_revenue,
        ]
        issues = []
        for check in checks:
            issues.extend(check(documents))
        logger.info("[VERIFY] %d documents analysés, %d anomalies détectées", len(documents), len(issues))
        return issues


_verifier = DocumentVerifier()


def verify_documents(documents: list[dict]) -> list[dict]:
    return _verifier.verify(documents)
