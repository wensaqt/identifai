from __future__ import annotations

from datetime import datetime


def _parse_date(date_str: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def verify_documents(documents: list[dict]) -> list[dict]:
    """Run inter-document checks on a batch of OCR results.

    Each document is a dict with at least: filename, doc_type, fields.
    Returns a list of issues: {type, severity, message, files}.
    """
    issues = []
    issues.extend(_check_siret_coherence(documents))
    issues.extend(_check_expired_attestations(documents))
    issues.extend(_check_tva_coherence(documents))
    issues.extend(_check_payment_amount(documents))
    issues.extend(_check_orphan_payments(documents))
    issues.extend(_check_declared_revenue(documents))
    return issues


def _check_siret_coherence(documents: list[dict]) -> list[dict]:
    issues = []

    invoices = [d for d in documents if d.get("doc_type") in ("facture", "devis", "invoice")]
    attestations = [d for d in documents if d.get("doc_type") in ("attestation_siret", "attestation_urssaf", "kbis")]

    if not invoices or not attestations:
        return issues

    invoice_sirets = set()
    for d in invoices:
        f = d.get("fields", {})
        s = f.get("siret_emetteur") or f.get("siret")
        if s:
            invoice_sirets.add(s)

    attestation_sirets = {d["fields"]["siret"] for d in attestations if d.get("fields", {}).get("siret")}

    mismatches = invoice_sirets.symmetric_difference(attestation_sirets)
    if mismatches:
        issues.append({
            "type": "siret_mismatch",
            "severity": "error",
            "message": f"SIRET incohérent entre factures/devis et attestations : {', '.join(mismatches)}",
            "files": [d["filename"] for d in documents
                      if (d.get("fields", {}).get("siret") in mismatches
                          or d.get("fields", {}).get("siret_emetteur") in mismatches)],
        })

    return issues


def _check_expired_attestations(documents: list[dict]) -> list[dict]:
    issues = []
    today = datetime.today()

    for doc in documents:
        if doc.get("doc_type") not in ("attestation_urssaf", "attestation_siret"):
            continue
        exp_str = doc.get("fields", {}).get("date_expiration")
        if not exp_str:
            continue
        exp_date = _parse_date(exp_str)
        if exp_date and exp_date < today:
            issues.append({
                "type": "expired_attestation",
                "severity": "error",
                "message": f"Attestation expirée depuis le {exp_str}",
                "files": [doc["filename"]],
            })

    return issues


def _check_tva_coherence(documents: list[dict]) -> list[dict]:
    """Check that montant_tva ≈ montant_ht * tva_rate on invoices."""
    issues = []

    for doc in documents:
        if doc.get("doc_type") not in ("facture", "invoice"):
            continue
        fields = doc.get("fields", {})
        ht = _safe_float(fields.get("montant_ht"))
        tva = _safe_float(fields.get("montant_tva"))
        rate = _safe_float(fields.get("tva_rate"))

        if ht is None or tva is None or rate is None:
            continue

        expected = round(ht * rate, 2)
        if abs(tva - expected) > 0.02:
            issues.append({
                "type": "tva_mismatch",
                "severity": "warning",
                "message": f"TVA incohérente : {tva} vs attendu {expected} (HT={ht}, taux={rate})",
                "files": [doc["filename"]],
            })

    return issues


def _check_payment_amount(documents: list[dict]) -> list[dict]:
    """Check that payment amount matches the referenced invoice TTC."""
    issues = []

    invoices = {
        d["fields"].get("invoice_id"): d
        for d in documents
        if d.get("doc_type") in ("facture", "invoice") and d.get("fields", {}).get("invoice_id")
    }

    for doc in documents:
        if doc.get("doc_type") != "payment":
            continue
        fields = doc.get("fields", {})
        ref = fields.get("reference_facture")
        if not ref or ref not in invoices:
            continue

        pay_amount = _safe_float(fields.get("montant"))
        inv_ttc = _safe_float(invoices[ref]["fields"].get("montant_ttc"))

        if pay_amount is not None and inv_ttc is not None and abs(pay_amount - inv_ttc) > 0.01:
            issues.append({
                "type": "payment_amount_mismatch",
                "severity": "error",
                "message": f"Paiement {pay_amount} != facture TTC {inv_ttc} (réf {ref})",
                "files": [doc["filename"], invoices[ref]["filename"]],
            })

    return issues


def _check_orphan_payments(documents: list[dict]) -> list[dict]:
    """Check for payments referencing non-existent invoices."""
    issues = []

    invoice_ids = {
        d["fields"].get("invoice_id")
        for d in documents
        if d.get("doc_type") in ("facture", "invoice") and d.get("fields", {}).get("invoice_id")
    }

    for doc in documents:
        if doc.get("doc_type") != "payment":
            continue
        ref = doc.get("fields", {}).get("reference_facture")
        if ref and ref not in invoice_ids:
            issues.append({
                "type": "orphan_payment",
                "severity": "warning",
                "message": f"Paiement référence une facture inexistante : {ref}",
                "files": [doc["filename"]],
            })

    return issues


def _check_declared_revenue(documents: list[dict]) -> list[dict]:
    """Check that declared CA is not significantly below invoiced HT total."""
    issues = []

    total_ht = 0.0
    for doc in documents:
        if doc.get("doc_type") not in ("facture", "invoice"):
            continue
        ht = _safe_float(doc.get("fields", {}).get("montant_ht"))
        if ht:
            total_ht += ht

    if total_ht == 0:
        return issues

    for doc in documents:
        if doc.get("doc_type") != "urssaf_declaration":
            continue
        declared = _safe_float(doc.get("fields", {}).get("chiffre_affaires_declare"))
        if declared is not None and declared < total_ht * 0.9:
            issues.append({
                "type": "undeclared_revenue",
                "severity": "warning",
                "message": f"CA déclaré ({declared}) inférieur à 90% du HT facturé ({total_ht})",
                "files": [doc["filename"]],
            })

    return issues
