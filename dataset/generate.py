from __future__ import annotations

import argparse
import json
import os
import random

from faker import Faker

from .builder import ScenarioBuilder
from .factories.company import CompanyFactory
from .factories.noise import NoiseLevel
from .scenarios import SCENARIOS


def _print_summary(output_dir: str) -> None:
    folders = sorted(d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d)))
    for name in folders:
        path = os.path.join(output_dir, name, "metadata.json")
        with open(path, encoding="utf-8") as fh:
            meta = json.load(fh)
        anomalies = [a["type"] for a in meta.get("anomalies_expected", [])]
        risk = meta.get("risk_level", "?")
        tag = "OK" if not anomalies else ", ".join(anomalies)
        print(f"  {name}/ [{risk}] — {tag}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fake French business documents")
    parser.add_argument("--output", default="dataset/output", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (default: random)")
    parser.add_argument(
        "--noise", default="none",
        choices=[level.value for level in NoiseLevel],
        help="Noise level for scan simulation (default: none)",
    )
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    fake = Faker("fr_FR")
    Faker.seed(seed)
    random.seed(seed)

    noise_level = NoiseLevel(args.noise)
    company_factory = CompanyFactory(fake)
    company = company_factory.create()
    client = company_factory.create()

    os.makedirs(args.output, exist_ok=True)

    builder = ScenarioBuilder(fake, args.output, noise_level)
    for scenario_def in SCENARIOS:
        builder.build(scenario_def, company, client)

    print(f"Company : {company.name} (SIRET {company.siret})")
    print(f"Client  : {client.name}")
    print(f"Noise   : {noise_level}")
    print(f"Output  : {args.output}/")
    _print_summary(args.output)


if __name__ == "__main__":
    main()
