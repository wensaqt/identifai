import argparse
import json
import os
import random

from faker import Faker

from .company import generate_company
from .documents import (
    generate_attestation_siret,
    generate_attestation_urssaf,
    generate_devis,
    generate_facture,
    generate_kbis,
    generate_rib,
)
from .noise import apply_noise


def main():
    parser = argparse.ArgumentParser(description="Generate fake French business documents")
    parser.add_argument("--count", type=int, default=10, help="Number of companies (6 docs each)")
    parser.add_argument("--output", default="dataset/output", help="Output directory")
    parser.add_argument("--noise", action="store_true", help="Apply scan noise to documents")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    fake = Faker("fr_FR")
    Faker.seed(args.seed)
    random.seed(args.seed)

    subdirs = ["facture", "devis", "attestation_siret", "attestation_urssaf", "kbis", "rib"]
    for d in subdirs:
        os.makedirs(os.path.join(args.output, d), exist_ok=True)

    metadata = []

    for i in range(args.count):
        company = generate_company(fake)
        client = generate_company(fake)
        idx = f"{i + 1:03d}"

        generators = [
            ("facture", lambda p: generate_facture(company, client, fake, p)),
            ("devis", lambda p: generate_devis(company, client, fake, p)),
            ("attestation_siret", lambda p: generate_attestation_siret(company, fake, p)),
            ("attestation_urssaf", lambda p: generate_attestation_urssaf(company, fake, p)),
            ("kbis", lambda p: generate_kbis(company, fake, p)),
            ("rib", lambda p: generate_rib(company, fake, p)),
        ]

        for doc_type, gen_func in generators:
            filename = f"{doc_type}_{idx}.pdf"
            filepath = os.path.join(args.output, doc_type, filename)

            meta = gen_func(filepath)
            meta["filename"] = f"{doc_type}/{filename}"

            if args.noise:
                level = random.choice(["light", "medium", "heavy"])
                noisy_path = filepath.replace(".pdf", "_noisy.pdf")
                apply_noise(filepath, noisy_path, level)
                meta["noise_level"] = level
                meta["noisy_filename"] = f"{doc_type}/{filename.replace('.pdf', '_noisy.pdf')}"

            metadata.append(meta)

    meta_path = os.path.join(args.output, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(metadata)} documents for {args.count} companies in {args.output}/")
    print(f"Metadata: {meta_path}")


if __name__ == "__main__":
    main()
