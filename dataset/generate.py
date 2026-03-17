from __future__ import annotations

import argparse
import json
import os
import random

from faker import Faker

from .factories.company import CompanyFactory, CompanyIdentity
from .factories.documents import (
    AttestationSiretFactory,
    AttestationUrssafFactory,
    DevisFactory,
    InvoiceFactory,
    KbisFactory,
    PaymentFactory,
    RibFactory,
    UrssafDeclarationFactory,
)
from .factories.noise import NoiseLevel, ScanSimulator


class ScenarioGenerator:

    def __init__(self, fake: Faker, output_dir: str, noise_level: NoiseLevel):
        self._fake = fake
        self._output_dir = output_dir
        self._noise = noise_level
        self._scanner = ScanSimulator()

        # Factories
        self._invoices = InvoiceFactory(fake)
        self._devis = DevisFactory(fake)
        self._attestation_siret = AttestationSiretFactory(fake)
        self._attestation_urssaf = AttestationUrssafFactory(fake)
        self._kbis = KbisFactory(fake)
        self._rib = RibFactory(fake)
        self._payments = PaymentFactory(fake)
        self._declarations = UrssafDeclarationFactory(fake)

    # ── Doc generation helpers ───────────────────────────────────────────

    def _generate_doc(self, folder: str, doc_type: str, gen_func) -> dict:
        filepath = os.path.join(folder, f"{doc_type}.pdf")
        meta = gen_func(filepath)
        self._apply_noise(filepath)
        meta["filename"] = f"{doc_type}.pdf"
        meta["noise_level"] = str(self._noise)
        return meta

    def _apply_noise(self, filepath: str) -> None:
        if self._noise == NoiseLevel.NONE:
            return
        noisy_path = filepath.replace(".pdf", "_scan.pdf")
        self._scanner.apply_noise(filepath, noisy_path, self._noise)
        os.remove(filepath)
        os.rename(noisy_path, filepath)

    def _write_scenario(self, name: str, meta: dict, doc_specs: list[tuple[str, callable]]) -> None:
        folder = os.path.join(self._output_dir, name)
        os.makedirs(folder, exist_ok=True)
        docs = [self._generate_doc(folder, dt, fn) for dt, fn in doc_specs]
        meta["noise_level"] = str(self._noise)
        meta["documents"] = docs
        with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _scenario_meta(self, scenario_type: str, description: str,
                       anomalies: list[str], risk: str, **extra) -> dict:
        meta = {
            "scenario_type": scenario_type,
            "description": description,
            "expected_anomalies": anomalies,
            "risk_level": risk,
        }
        meta.update(extra)
        return meta

    # ── Scenarios ────────────────────────────────────────────────────────

    def happy_path(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        invoice_meta = {}

        def _invoice(p):
            m = self._invoices.create(company, client, p, statut_paiement="paid", reference_paiement="PAY-PENDING")
            invoice_meta.update(m)
            return m

        def _payment(p):
            return self._payments.create(company, client, p,
                                         invoice_id=invoice_meta.get("invoice_id"),
                                         montant=invoice_meta.get("montant_ttc"))

        def _declaration(p):
            return self._declarations.create(company, p,
                                             chiffre_affaires=invoice_meta.get("montant_ht"))

        self._write_scenario("happy_path",
            self._scenario_meta("happy_path",
                "Tous les documents sont cohérents. Facture payée, paiement correspondant, déclaration URSSAF correcte.",
                [], "low"),
            [
                ("invoice", _invoice),
                ("devis", lambda p: self._devis.create(company, client, p)),
                ("payment", _payment),
                ("urssaf_declaration", _declaration),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
                ("attestation_urssaf", lambda p: self._attestation_urssaf.create(company, p)),
                ("kbis", lambda p: self._kbis.create(company, p)),
                ("rib", lambda p: self._rib.create(company, p)),
            ])

    def missing_payment(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        self._write_scenario("missing_payment",
            self._scenario_meta("missing_payment",
                "Facture impayée sans justificatif de paiement.",
                ["missing_payment"], "medium"),
            [
                ("invoice", lambda p: self._invoices.create(company, client, p, statut_paiement="unpaid")),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
                ("attestation_urssaf", lambda p: self._attestation_urssaf.create(company, p)),
            ])

    def mauvais_siret(self, company: CompanyIdentity, client: CompanyIdentity,
                      company_factory: CompanyFactory) -> None:
        bad = company_factory.with_wrong_siret(company)
        self._write_scenario("mauvais_siret",
            self._scenario_meta("mauvais_siret",
                "Le SIRET de la facture ne correspond pas aux attestations.",
                ["siret_mismatch"], "high",
                bad_siret=bad.siret, expected_siret=company.siret),
            [
                ("invoice", lambda p: self._invoices.create(bad, client, p)),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
                ("attestation_urssaf", lambda p: self._attestation_urssaf.create(company, p)),
                ("kbis", lambda p: self._kbis.create(company, p)),
            ])

    def revenus_sous_declares(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        invoice_meta = {}

        def _invoice(p):
            m = self._invoices.create(company, client, p, statut_paiement="paid")
            invoice_meta.update(m)
            return m

        def _declaration(p):
            real_ht = invoice_meta.get("montant_ht", 10000)
            declared = round(real_ht * random.uniform(0.3, 0.6), 2)
            return self._declarations.create(company, p, chiffre_affaires=declared)

        self._write_scenario("revenus_sous_declares",
            self._scenario_meta("revenus_sous_declares",
                "Le CA déclaré à l'URSSAF est inférieur au montant HT facturé.",
                ["undeclared_revenue"], "high"),
            [
                ("invoice", _invoice),
                ("urssaf_declaration", _declaration),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
            ])

    def incoherence_tva(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        wrong_tva = round(random.uniform(500, 2000), 2)
        self._write_scenario("incoherence_tva",
            self._scenario_meta("incoherence_tva",
                "Le montant de TVA ne correspond pas au taux appliqué sur le HT.",
                ["tva_mismatch"], "medium"),
            [
                ("invoice", lambda p: self._invoices.create(company, client, p, override_tva=wrong_tva)),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
            ])

    def attestation_expiree(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        self._write_scenario("attestation_expiree",
            self._scenario_meta("attestation_expiree",
                "L'attestation URSSAF est expirée.",
                ["expired_attestation"], "high"),
            [
                ("invoice", lambda p: self._invoices.create(company, client, p)),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
                ("attestation_urssaf", lambda p: self._attestation_urssaf.create_expired(company, p)),
                ("kbis", lambda p: self._kbis.create(company, p)),
            ])

    def paiement_sans_facture(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        self._write_scenario("paiement_sans_facture",
            self._scenario_meta("paiement_sans_facture",
                "Un paiement référence une facture inexistante.",
                ["orphan_payment"], "medium"),
            [
                ("payment", lambda p: self._payments.create(company, client, p, invoice_id="F-0000-0000")),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
            ])

    def montant_paiement_incorrect(self, company: CompanyIdentity, client: CompanyIdentity) -> None:
        invoice_meta = {}

        def _invoice(p):
            m = self._invoices.create(company, client, p, statut_paiement="paid")
            invoice_meta.update(m)
            return m

        def _payment(p):
            wrong = round(invoice_meta.get("montant_ttc", 1000) * random.uniform(0.5, 0.9), 2)
            return self._payments.create(company, client, p,
                                         invoice_id=invoice_meta.get("invoice_id"), montant=wrong)

        self._write_scenario("montant_paiement_incorrect",
            self._scenario_meta("montant_paiement_incorrect",
                "Le montant du paiement ne correspond pas au TTC de la facture.",
                ["payment_amount_mismatch"], "medium"),
            [
                ("invoice", _invoice),
                ("payment", _payment),
                ("attestation_siret", lambda p: self._attestation_siret.create(company, p)),
            ])

    def generate_all(self, company: CompanyIdentity, client: CompanyIdentity,
                     company_factory: CompanyFactory) -> None:
        self.happy_path(company, client)
        self.missing_payment(company, client)
        self.mauvais_siret(company, client, company_factory)
        self.revenus_sous_declares(company, client)
        self.incoherence_tva(company, client)
        self.attestation_expiree(company, client)
        self.paiement_sans_facture(company, client)
        self.montant_paiement_incorrect(company, client)


def _print_summary(output_dir: str, company: CompanyIdentity, client: CompanyIdentity,
                   noise_level: NoiseLevel) -> None:
    print(f"Company: {company.name} (SIRET {company.siret})")
    print(f"Client : {client.name}")
    print(f"Noise  : {noise_level}")
    print(f"Output : {output_dir}/")
    folders = sorted(d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d)))
    for f in folders:
        with open(os.path.join(output_dir, f, "metadata.json")) as fh:
            meta = json.load(fh)
        anomalies = meta.get("expected_anomalies", [])
        risk = meta.get("risk_level", "?")
        tag = "OK" if not anomalies else ", ".join(anomalies)
        print(f"  {f}/ [{risk}] — {tag}")


def main():
    parser = argparse.ArgumentParser(description="Generate fake French business documents")
    parser.add_argument("--output", default="dataset/output", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (default: random)")
    parser.add_argument("--noise", default="none",
                        choices=[level.value for level in NoiseLevel],
                        help="Noise level for scan simulation (default: none)")
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

    generator = ScenarioGenerator(fake, args.output, noise_level)
    generator.generate_all(company, client, company_factory)

    _print_summary(args.output, company, client, noise_level)


if __name__ == "__main__":
    main()
