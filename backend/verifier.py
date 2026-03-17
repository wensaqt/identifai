from __future__ import annotations

from datetime import datetime


def _parse_date(date_str: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def verify_documents(documents: list[dict]) -> list[dict]:
    """Run inter-document checks on a batch of OCR results.

    Each document is a dict with at least: filename, doc_type, fields.
    Returns a list of issues: {type, severity, message, files}.
    """
    issues = []

    issues.extend(_check_siret_coherence(documents))
    issues.extend(_check_expired_attestations(documents))
    issues.extend(_check_missing_fields(documents))
    print(issues)
    return issues


def _check_siret_coherence(documents: list[dict]) -> list[dict]:
    issues = []
    siret_map: dict[str, list[str]] = {}

    for doc in documents:
        siret = doc.get("fields", {}).get("siret")
        if siret:
            siret_map.setdefault(siret, []).append(doc["filename"])

    # Si plusieurs documents ont des SIRET différents alors qu'ils devraient
    # provenir du même fournisseur (facture + attestation dans le même batch)
    invoices = [d for d in documents if d.get("doc_type") in ("facture", "devis")]
    attestations = [d for d in documents if d.get("doc_type") in ("attestation_siret", "attestation_urssaf", "kbis")]

    if not invoices or not attestations:
        return issues

    invoice_sirets = {d["fields"]["siret"] for d in invoices if d.get("fields", {}).get("siret")}
    attestation_sirets = {d["fields"]["siret"] for d in attestations if d.get("fields", {}).get("siret")}

    mismatches = invoice_sirets.symmetric_difference(attestation_sirets)
    if mismatches:
        issues.append({
            "type": "siret_mismatch",
            "severity": "error",
            "message": f"SIRET incohérent entre factures/devis et attestations : {', '.join(mismatches)}",
            "files": [d["filename"] for d in documents if d.get("fields", {}).get("siret") in mismatches],
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


def _check_missing_fields(documents: list[dict]) -> list[dict]:
    issues = []

    required: dict[str, list[str]] = {
        "facture": ["siret", "montant_ht", "montant_ttc", "date_emission"],
        "devis": ["siret", "montant_ht", "date_emission"],
        "attestation_urssaf": ["siret", "date_expiration"],
        "attestation_siret": ["siret"],
        "kbis": ["siret"],
        "rib": ["iban"],
    }

    for doc in documents:
        doc_type = doc.get("doc_type")
        if not doc_type or doc_type not in required:
            continue
        fields = doc.get("fields", {})
        missing = [f for f in required[doc_type] if not fields.get(f)]
        if missing:
            issues.append({
                "type": "missing_fields",
                "severity": "warning",
                "message": f"Champs manquants ({doc_type}) : {', '.join(missing)}",
                "files": [doc["filename"]],
            })

    return issues
