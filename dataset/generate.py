from __future__ import annotations

import argparse
import json
import os
import random

from faker import Faker

from .company import generate_company, with_wrong_siret
from .documents import (
    generate_attestation_siret,
    generate_attestation_urssaf,
    generate_attestation_urssaf_expired,
    generate_devis,
    generate_facture,
    generate_kbis,
    generate_payment,
    generate_rib,
    generate_urssaf_declaration,
)
from .noise import apply_noise


def _generate_docs(generators, output_dir, noise_level):
    """Generate all docs into output_dir, apply noise, return metadata list."""
    os.makedirs(output_dir, exist_ok=True)
    docs_meta = []

    for doc_type, gen_func in generators:
        filepath = os.path.join(output_dir, f"{doc_type}.pdf")
        meta = gen_func(filepath)

        noisy_path = filepath.replace(".pdf", "_scan.pdf")
        apply_noise(filepath, noisy_path, noise_level)
        os.remove(filepath)
        os.rename(noisy_path, filepath)

        meta["filename"] = f"{doc_type}.pdf"
        meta["noise_level"] = noise_level
        docs_meta.append(meta)

    return docs_meta


def _write_scenario(output_dir, name, scenario_meta, generators, noise_level):
    """Generate a full scenario folder with docs + metadata.json."""
    folder = os.path.join(output_dir, name)
    docs = _generate_docs(generators, folder, noise_level)
    scenario_meta["noise_level"] = noise_level
    scenario_meta["documents"] = docs
    with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(scenario_meta, f, ensure_ascii=False, indent=2)
    return docs


# ── Scenarios ────────────────────────────────────────────────────────────────

def _happy_path(company, client, fake, output_dir, noise_level):
    """All documents coherent, invoice paid, matching payment, correct declaration."""
    # Generate facture first to get amounts
    invoice_meta = {}

    def _facture(p):
        m = generate_facture(company, client, fake, p,
                             statut_paiement="paid", reference_paiement="PAY-PENDING")
        invoice_meta.update(m)
        return m

    def _payment(p):
        return generate_payment(company, client, fake, p,
                                invoice_id=invoice_meta.get("invoice_id"),
                                montant=invoice_meta.get("montant_ttc"))

    def _declaration(p):
        return generate_urssaf_declaration(company, fake, p,
                                           chiffre_affaires=invoice_meta.get("montant_ht"))

    generators = [
        ("invoice", _facture),
        ("devis", lambda p: generate_devis(company, client, fake, p)),
        ("payment", _payment),
        ("urssaf_declaration", _declaration),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
        ("rib", lambda p: generate_rib(company, fake, p)),
    ]

    _write_scenario(output_dir, "happy_path", {
        "scenario_type": "happy_path",
        "description": "Tous les documents sont cohérents. Facture payée, paiement correspondant, déclaration URSSAF correcte.",
        "expected_anomalies": [],
        "risk_level": "low",
    }, generators, noise_level)


def _missing_payment(company, client, fake, output_dir, noise_level):
    """Invoice unpaid, no payment document."""
    generators = [
        ("invoice", lambda p: generate_facture(company, client, fake, p, statut_paiement="unpaid")),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
    ]

    _write_scenario(output_dir, "missing_payment", {
        "scenario_type": "missing_payment",
        "description": "Facture impayée sans justificatif de paiement.",
        "expected_anomalies": ["missing_payment"],
        "risk_level": "medium",
    }, generators, noise_level)


def _mauvais_siret(company, client, fake, output_dir, noise_level):
    """SIRET on invoice doesn't match attestation SIRET."""
    bad = with_wrong_siret(company, fake)

    generators = [
        ("invoice", lambda p: generate_facture(bad, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
    ]

    _write_scenario(output_dir, "mauvais_siret", {
        "scenario_type": "mauvais_siret",
        "description": "Le SIRET de la facture ne correspond pas aux attestations.",
        "expected_anomalies": ["siret_mismatch"],
        "risk_level": "high",
        "bad_siret": bad.siret,
        "expected_siret": company.siret,
    }, generators, noise_level)


def _revenus_sous_declares(company, client, fake, output_dir, noise_level):
    """URSSAF declaration CA is significantly lower than actual invoiced amount."""
    invoice_meta = {}

    def _facture(p):
        m = generate_facture(company, client, fake, p, statut_paiement="paid")
        invoice_meta.update(m)
        return m

    def _declaration(p):
        real_ht = invoice_meta.get("montant_ht", 10000)
        declared = round(real_ht * random.uniform(0.3, 0.6), 2)
        return generate_urssaf_declaration(company, fake, p, chiffre_affaires=declared)

    generators = [
        ("invoice", _facture),
        ("urssaf_declaration", _declaration),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
    ]

    _write_scenario(output_dir, "revenus_sous_declares", {
        "scenario_type": "revenus_sous_declares",
        "description": "Le CA déclaré à l'URSSAF est inférieur au montant HT facturé.",
        "expected_anomalies": ["undeclared_revenue"],
        "risk_level": "high",
    }, generators, noise_level)


def _incoherence_tva(company, client, fake, output_dir, noise_level):
    """TVA amount on invoice doesn't match rate * HT."""
    wrong_tva = round(random.uniform(500, 2000), 2)

    generators = [
        ("invoice", lambda p: generate_facture(company, client, fake, p, override_tva=wrong_tva)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
    ]

    _write_scenario(output_dir, "incoherence_tva", {
        "scenario_type": "incoherence_tva",
        "description": "Le montant de TVA ne correspond pas au taux appliqué sur le HT.",
        "expected_anomalies": ["tva_mismatch"],
        "risk_level": "medium",
    }, generators, noise_level)


def _attestation_expiree(company, client, fake, output_dir, noise_level):
    """Expired URSSAF attestation."""
    generators = [
        ("invoice", lambda p: generate_facture(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf_expired(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
    ]

    _write_scenario(output_dir, "attestation_expiree", {
        "scenario_type": "attestation_expiree",
        "description": "L'attestation URSSAF est expirée.",
        "expected_anomalies": ["expired_attestation"],
        "risk_level": "high",
    }, generators, noise_level)


def _paiement_sans_facture(company, client, fake, output_dir, noise_level):
    """Payment references a non-existent invoice."""
    generators = [
        ("payment", lambda p: generate_payment(company, client, fake, p,
                                                invoice_id="F-0000-0000")),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
    ]

    _write_scenario(output_dir, "paiement_sans_facture", {
        "scenario_type": "paiement_sans_facture",
        "description": "Un paiement référence une facture inexistante.",
        "expected_anomalies": ["orphan_payment"],
        "risk_level": "medium",
    }, generators, noise_level)


def _montant_paiement_incorrect(company, client, fake, output_dir, noise_level):
    """Payment amount doesn't match invoice TTC."""
    invoice_meta = {}

    def _facture(p):
        m = generate_facture(company, client, fake, p, statut_paiement="paid")
        invoice_meta.update(m)
        return m

    def _payment(p):
        wrong_amount = round(invoice_meta.get("montant_ttc", 1000) * random.uniform(0.5, 0.9), 2)
        return generate_payment(company, client, fake, p,
                                invoice_id=invoice_meta.get("invoice_id"),
                                montant=wrong_amount)

    generators = [
        ("invoice", _facture),
        ("payment", _payment),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
    ]

    _write_scenario(output_dir, "montant_paiement_incorrect", {
        "scenario_type": "montant_paiement_incorrect",
        "description": "Le montant du paiement ne correspond pas au TTC de la facture.",
        "expected_anomalies": ["payment_amount_mismatch"],
        "risk_level": "medium",
    }, generators, noise_level)


ALL_SCENARIOS = [
    _happy_path,
    _missing_payment,
    _mauvais_siret,
    _revenus_sous_declares,
    _incoherence_tva,
    _attestation_expiree,
    _paiement_sans_facture,
    _montant_paiement_incorrect,
]


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate fake French business documents")
    parser.add_argument("--output", default="dataset/output", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (default: random)")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    fake = Faker("fr_FR")
    Faker.seed(seed)
    random.seed(seed)

    company = generate_company(fake)
    client = generate_company(fake)
    noise_level = random.choice(["light", "medium", "heavy"])

    os.makedirs(args.output, exist_ok=True)

    for scenario_fn in ALL_SCENARIOS:
        scenario_fn(company, client, fake, args.output, noise_level)

    # Summary
    print(f"Company: {company.name} (SIRET {company.siret})")
    print(f"Client : {client.name}")
    print(f"Noise  : {noise_level}")
    print(f"Output : {args.output}/")
    folders = sorted(d for d in os.listdir(args.output) if os.path.isdir(os.path.join(args.output, d)))
    for f in folders:
        meta_path = os.path.join(args.output, f, "metadata.json")
        with open(meta_path) as fh:
            meta = json.load(fh)
        anomalies = meta.get("expected_anomalies", [])
        risk = meta.get("risk_level", "?")
        tag = "OK" if not anomalies else ", ".join(anomalies)
        print(f"  {f}/ [{risk}] — {tag}")


if __name__ == "__main__":
    main()
