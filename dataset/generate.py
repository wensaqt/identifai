import argparse
import json
import os
import random
import re
import unicodedata

from faker import Faker

from .company import (
    generate_company,
    with_wrong_iban,
    with_wrong_siret,
)
from .documents import (
    generate_attestation_siret,
    generate_attestation_urssaf,
    generate_attestation_urssaf_expired,
    generate_attestation_urssaf_no_expiry,
    generate_devis,
    generate_facture,
    generate_facture_no_amounts,
    generate_kbis,
    generate_rib,
    generate_rib_no_iban,
)
from .noise import apply_noise


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "_", text)[:40]


def _generate_docs(generators, output_dir, noise_level):
    """Generate all docs into output_dir, apply noise, return metadata list."""
    os.makedirs(output_dir, exist_ok=True)
    docs_meta = []

    for doc_type, gen_func in generators:
        filepath = os.path.join(output_dir, f"{doc_type}.pdf")
        meta = gen_func(filepath)

        # Apply noise to simulate scanned documents
        noisy_path = filepath.replace(".pdf", "_scan.pdf")
        apply_noise(filepath, noisy_path, noise_level)

        # Remove clean PDF, keep only the scanned version
        os.remove(filepath)
        os.rename(noisy_path, filepath)

        meta["filename"] = f"{doc_type}.pdf"
        meta["noise_level"] = noise_level
        docs_meta.append(meta)

    return docs_meta


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
    slug = _slugify(company.name)

    noise_level = random.choice(["light", "medium", "heavy"])

    # ── 1. Clean folder: all documents are coherent ──────────────────────
    clean_name = f"{slug}_clean"
    clean_dir = os.path.join(args.output, clean_name)

    clean_generators = [
        ("facture", lambda p: generate_facture(company, client, fake, p)),
        ("devis", lambda p: generate_devis(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
        ("rib", lambda p: generate_rib(company, fake, p)),
    ]

    clean_docs = _generate_docs(clean_generators, clean_dir, noise_level)

    clean_meta = {
        "company_name": company.name,
        "company_siret": company.siret,
        "scenario": "clean",
        "errors": [],
        "noise_level": noise_level,
        "documents": clean_docs,
    }
    with open(os.path.join(clean_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(clean_meta, f, ensure_ascii=False, indent=2)

    bad_company = with_wrong_siret(company, fake)
    bad_company_rib = with_wrong_iban(company, fake)

    # ── 2. SIRET mismatch: facture SIRET differs from attestations ────────
    # ATTENDU : alerte siret_mismatch sur facture.pdf + attestation_siret.pdf
    siret_mismatch_name = f"{slug}_ERR_siret_mismatch"
    siret_mismatch_dir = os.path.join(args.output, siret_mismatch_name)
    siret_mismatch_generators = [
        ("facture", lambda p: generate_facture(bad_company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
    ]
    sm_docs = _generate_docs(siret_mismatch_generators, siret_mismatch_dir, noise_level)
    with open(os.path.join(siret_mismatch_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_siret_mismatch", "expected_alerts": ["siret_mismatch"],
                   "company_siret": company.siret, "bad_siret": bad_company.siret,
                   "noise_level": noise_level, "documents": sm_docs}, f, ensure_ascii=False, indent=2)

    # ── 3. Expired attestation URSSAF ─────────────────────────────────────
    # ATTENDU : alerte expired_attestation sur attestation_urssaf.pdf
    expired_name = f"{slug}_ERR_attestation_expired"
    expired_dir = os.path.join(args.output, expired_name)
    expired_generators = [
        ("facture", lambda p: generate_facture(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf_expired(company, fake, p)),
    ]
    exp_docs = _generate_docs(expired_generators, expired_dir, noise_level)
    with open(os.path.join(expired_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_attestation_expired", "expected_alerts": ["expired_attestation"],
                   "noise_level": noise_level, "documents": exp_docs}, f, ensure_ascii=False, indent=2)

    # ── 4. All errors combined ────────────────────────────────────────────
    # ATTENDU : siret_mismatch + expired_attestation + missing_fields (rib sans iban)
    all_errors_name = f"{slug}_ERR_all"
    all_errors_dir = os.path.join(args.output, all_errors_name)
    all_errors_generators = [
        ("facture", lambda p: generate_facture(bad_company, client, fake, p)),
        ("devis", lambda p: generate_devis(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf_expired(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
        ("rib", lambda p: generate_rib(bad_company_rib, fake, p)),
    ]
    all_docs = _generate_docs(all_errors_generators, all_errors_dir, noise_level)
    with open(os.path.join(all_errors_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_all", "expected_alerts": ["siret_mismatch", "expired_attestation"],
                   "noise_level": noise_level, "documents": all_docs}, f, ensure_ascii=False, indent=2)

    # ── 5. Missing fields: facture sans montants ──────────────────────────
    # ATTENDU : missing_fields sur facture.pdf (montant_ht, montant_ttc)
    mf_facture_name = f"{slug}_ERR_missing_fields_facture"
    mf_facture_dir = os.path.join(args.output, mf_facture_name)
    mf_facture_generators = [
        ("facture", lambda p: generate_facture_no_amounts(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
    ]
    mf_facture_docs = _generate_docs(mf_facture_generators, mf_facture_dir, noise_level)
    with open(os.path.join(mf_facture_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_missing_fields_facture",
                   "expected_alerts": ["missing_fields"],
                   "missing": ["montant_ht", "montant_ttc"],
                   "noise_level": noise_level, "documents": mf_facture_docs}, f, ensure_ascii=False, indent=2)

    # ── 6. Missing fields: RIB sans IBAN ─────────────────────────────────
    # ATTENDU : missing_fields sur rib.pdf (iban)
    mf_rib_name = f"{slug}_ERR_missing_fields_rib"
    mf_rib_dir = os.path.join(args.output, mf_rib_name)
    mf_rib_generators = [
        ("rib", lambda p: generate_rib_no_iban(company, fake, p)),
    ]
    mf_rib_docs = _generate_docs(mf_rib_generators, mf_rib_dir, noise_level)
    with open(os.path.join(mf_rib_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_missing_fields_rib",
                   "expected_alerts": ["missing_fields"],
                   "missing": ["iban"],
                   "noise_level": noise_level, "documents": mf_rib_docs}, f, ensure_ascii=False, indent=2)

    # ── 7. Missing fields: attestation URSSAF sans date d'expiration ──────
    # ATTENDU : missing_fields sur attestation_urssaf.pdf (date_expiration)
    mf_urssaf_name = f"{slug}_ERR_missing_fields_urssaf"
    mf_urssaf_dir = os.path.join(args.output, mf_urssaf_name)
    mf_urssaf_generators = [
        ("attestation_urssaf", lambda p: generate_attestation_urssaf_no_expiry(company, fake, p)),
    ]
    mf_urssaf_docs = _generate_docs(mf_urssaf_generators, mf_urssaf_dir, noise_level)
    with open(os.path.join(mf_urssaf_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"scenario": "ERR_missing_fields_urssaf",
                   "expected_alerts": ["missing_fields"],
                   "missing": ["date_expiration"],
                   "noise_level": noise_level, "documents": mf_urssaf_docs}, f, ensure_ascii=False, indent=2)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"Company  : {company.name} (SIRET {company.siret})")
    print(f"Bad SIRET: {bad_company.siret}")
    print(f"Noise    : {noise_level}")
    print(f"  {clean_name}/                  — ✅ tous cohérents")
    print(f"  {siret_mismatch_name}/  — 🔴 siret_mismatch")
    print(f"  {expired_name}/   — 🔴 expired_attestation")
    print(f"  {all_errors_name}/                     — 🔴 siret_mismatch + expired_attestation")
    print(f"  {mf_facture_name}/ — 🔴 missing_fields (montant_ht, montant_ttc)")
    print(f"  {mf_rib_name}/     — 🔴 missing_fields (iban)")
    print(f"  {mf_urssaf_name}/  — 🔴 missing_fields (date_expiration)")


if __name__ == "__main__":
    main()
