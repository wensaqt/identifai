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
    generate_devis,
    generate_facture,
    generate_kbis,
    generate_rib,
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

    # ── 2. Errors folder: same company, multiple injected errors ─────────
    errors_name = f"{slug}_errors"
    errors_dir = os.path.join(args.output, errors_name)

    bad_company_facture = with_wrong_siret(company, fake)
    bad_company_rib = with_wrong_iban(company, fake)

    errors_generators = [
        ("facture", lambda p: generate_facture(bad_company_facture, client, fake, p)),
        ("devis", lambda p: generate_devis(company, client, fake, p)),
        ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
        ("attestation_urssaf", lambda p: generate_attestation_urssaf_expired(company, fake, p)),
        ("kbis", lambda p: generate_kbis(company, fake, p)),
        ("rib", lambda p: generate_rib(bad_company_rib, fake, p)),
    ]

    errors_docs = _generate_docs(errors_generators, errors_dir, noise_level)

    errors_meta = {
        "company_name": company.name,
        "company_siret": company.siret,
        "scenario": "errors",
        "errors": ["siret_mismatch_facture", "expired_urssaf", "wrong_iban"],
        "noise_level": noise_level,
        "documents": errors_docs,
    }
    with open(os.path.join(errors_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(errors_meta, f, ensure_ascii=False, indent=2)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"Company: {company.name} (SIRET {company.siret})")
    print(f"Noise level: {noise_level}")
    print(f"  {clean_name}/  — 6 docs, all coherent")
    print(f"  {errors_name}/ — 6 docs, 3 injected errors:")
    print(f"    - facture SIRET mismatch")
    print(f"    - attestation URSSAF expired")
    print(f"    - RIB IBAN mismatch")


if __name__ == "__main__":
    main()
