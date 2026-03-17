from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from typing import Callable

from faker import Faker

from .consts import AnomalyType, DocType, FieldName as F
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
from .models import (
    AnomalyDetail,
    DocumentRecord,
    ScenarioDefinition,
    ScenarioDocSpec,
    ScenarioMetadata,
)

# Required fields per doc type — mirrors DOC_TYPE_MODELS.REQUIRED_FIELDS (backend/models.py)
_REQUIRED_FIELDS: dict[DocType, list[F]] = {
    DocType.INVOICE: [F.INVOICE_ID, F.SIRET_EMETTEUR, F.MONTANT_HT, F.MONTANT_TTC, F.DATE_EMISSION],
    DocType.DEVIS: [F.SIRET_EMETTEUR, F.MONTANT_HT, F.DATE_EMISSION],
    DocType.ATTESTATION_SIRET: [F.SIRET],
    DocType.ATTESTATION_URSSAF: [F.SIRET, F.DATE_EXPIRATION],
    DocType.KBIS: [F.SIRET, F.SIREN],
    DocType.RIB: [F.IBAN],
    DocType.PAYMENT: [F.MONTANT, F.DATE_PAIEMENT],
    DocType.URSSAF_DECLARATION: [F.SIRET, F.PERIODE, F.CHIFFRE_AFFAIRES_DECLARE, F.DATE_DECLARATION],
}

# Callable signatures for dispatch tables
_DocBuilder = Callable[["AnomalyType | None", str, "_BuildContext"], dict]
_AnomalyBuilder = Callable[["list[DocumentRecord]", "_BuildContext"], AnomalyDetail]

# Orphan payment sentinel — invoice ID that will never exist
_ORPHAN_INVOICE_ID = "F-0000-0000"


@dataclass
class _BuildContext:
    """Mutable state shared across document builders within one scenario."""
    company: CompanyIdentity
    client: CompanyIdentity
    has_payment: bool = False
    invoice_meta: dict = field(default_factory=dict)
    wrong_siret_company: CompanyIdentity | None = None


class ScenarioBuilder:
    """Builds one scenario at a time: generates PDFs, validates fields, writes metadata.json."""

    def __init__(self, fake: Faker, output_dir: str, noise_level: NoiseLevel) -> None:
        self._output_dir = output_dir
        self._noise = noise_level
        self._scanner = ScanSimulator()
        self._company_factory = CompanyFactory(fake)

        self._invoice_factory = InvoiceFactory(fake)
        self._devis_factory = DevisFactory(fake)
        self._att_siret_factory = AttestationSiretFactory(fake)
        self._att_urssaf_factory = AttestationUrssafFactory(fake)
        self._kbis_factory = KbisFactory(fake)
        self._rib_factory = RibFactory(fake)
        self._payment_factory = PaymentFactory(fake)
        self._declaration_factory = UrssafDeclarationFactory(fake)

        self._factory_handlers: dict[str, _DocBuilder] = self._make_factory_handlers()
        self._anomaly_builders: dict[AnomalyType, _AnomalyBuilder] = self._make_anomaly_builders()

    # ── Dispatch tables ───────────────────────────────────────────────────

    def _make_factory_handlers(self) -> dict[str, _DocBuilder]:
        return {
            DocType.INVOICE: self._build_invoice,
            DocType.DEVIS: self._build_devis,
            DocType.ATTESTATION_SIRET: self._build_attestation_siret,
            DocType.ATTESTATION_URSSAF: self._build_attestation_urssaf,
            DocType.KBIS: self._build_kbis,
            DocType.RIB: self._build_rib,
            DocType.PAYMENT: self._build_payment,
            DocType.URSSAF_DECLARATION: self._build_declaration,
        }

    def _make_anomaly_builders(self) -> dict[AnomalyType, _AnomalyBuilder]:
        return {
            AnomalyType.SIRET_MISMATCH: self._detail_siret_mismatch,
            AnomalyType.UNDECLARED_REVENUE: self._detail_undeclared_revenue,
            AnomalyType.TVA_MISMATCH: self._detail_tva_mismatch,
            AnomalyType.PAYMENT_AMOUNT_MISMATCH: self._detail_payment_amount_mismatch,
            AnomalyType.ORPHAN_PAYMENT: self._detail_orphan_payment,
            AnomalyType.EXPIRED_ATTESTATION: self._detail_expired_attestation,
            AnomalyType.MISSING_PAYMENT: self._detail_missing_payment,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def build(
        self,
        definition: ScenarioDefinition,
        company: CompanyIdentity,
        client: CompanyIdentity,
    ) -> ScenarioMetadata:
        """Generate all documents, validate them, and write metadata.json."""
        folder = os.path.join(self._output_dir, definition.name)
        os.makedirs(folder, exist_ok=True)

        ctx = self._init_context(definition, company, client)
        records = [self._build_doc(spec, folder, ctx) for spec in definition.doc_specs]
        self._validate_records(records)

        metadata = self._build_metadata(definition, records, ctx)
        self._write_metadata(folder, metadata)
        return metadata

    # ── Context ───────────────────────────────────────────────────────────

    def _init_context(
        self,
        definition: ScenarioDefinition,
        company: CompanyIdentity,
        client: CompanyIdentity,
    ) -> _BuildContext:
        ctx = _BuildContext(
            company=company,
            client=client,
            has_payment=any(s.doc_type == DocType.PAYMENT for s in definition.doc_specs),
        )
        if AnomalyType.SIRET_MISMATCH in definition.anomaly_types:
            ctx.wrong_siret_company = self._company_factory.with_wrong_siret(company)
        return ctx

    # ── Document building ─────────────────────────────────────────────────

    def _build_doc(self, spec: ScenarioDocSpec, folder: str, ctx: _BuildContext) -> DocumentRecord:
        filepath = os.path.join(folder, f"{spec.doc_type}.pdf")
        handler = self._factory_handlers.get(spec.doc_type)
        if handler is None:
            raise ValueError(f"Unknown doc_type: {spec.doc_type!r}")
        raw = handler(spec.anomaly, filepath, ctx)
        self._apply_noise(filepath)
        fields = {k: v for k, v in raw.items() if k not in ("type", "filename", "noise_level")}
        return DocumentRecord(
            doc_id=uuid.uuid4().hex[:8],
            doc_type=spec.doc_type,
            filename=f"{spec.doc_type}.pdf",
            fields=fields,
        )

    # ── Per-doc-type builders ─────────────────────────────────────────────

    def _build_invoice(self, anomaly: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        if anomaly == AnomalyType.SIRET_MISMATCH:
            meta = self._invoice_factory.create(ctx.wrong_siret_company, ctx.client, filepath)
        elif anomaly == AnomalyType.TVA_MISMATCH:
            wrong_tva = round(random.uniform(500, 2000), 2)
            meta = self._invoice_factory.create(ctx.company, ctx.client, filepath, override_tva=wrong_tva)
        elif anomaly == AnomalyType.MISSING_PAYMENT:
            meta = self._invoice_factory.create(ctx.company, ctx.client, filepath, statut_paiement="paid")
        else:
            statut = "paid" if ctx.has_payment else "unpaid"
            meta = self._invoice_factory.create(
                ctx.company, ctx.client, filepath, statut_paiement=statut,
            )
        ctx.invoice_meta.update(meta)  # subsequent builders (payment, declaration) read from here
        return meta

    def _build_devis(self, _: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        return self._devis_factory.create(ctx.company, ctx.client, filepath)

    def _build_attestation_siret(self, _: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        return self._att_siret_factory.create(ctx.company, filepath)

    def _build_attestation_urssaf(self, anomaly: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        if anomaly == AnomalyType.EXPIRED_ATTESTATION:
            return self._att_urssaf_factory.create_expired(ctx.company, filepath)
        return self._att_urssaf_factory.create(ctx.company, filepath)

    def _build_kbis(self, _: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        return self._kbis_factory.create(ctx.company, filepath)

    def _build_rib(self, _: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        return self._rib_factory.create(ctx.company, filepath)

    def _build_payment(self, anomaly: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        if anomaly == AnomalyType.ORPHAN_PAYMENT:
            return self._payment_factory.create(
                ctx.company, ctx.client, filepath, invoice_id=_ORPHAN_INVOICE_ID,
            )
        if anomaly == AnomalyType.PAYMENT_AMOUNT_MISMATCH:
            wrong_amount = round(ctx.invoice_meta.get(F.MONTANT_TTC, 1000) * random.uniform(0.5, 0.9), 2)
            return self._payment_factory.create(
                ctx.company, ctx.client, filepath,
                invoice_id=ctx.invoice_meta.get(F.INVOICE_ID),
                montant=wrong_amount,
            )
        return self._payment_factory.create(
            ctx.company, ctx.client, filepath,
            invoice_id=ctx.invoice_meta.get(F.INVOICE_ID),
            montant=ctx.invoice_meta.get(F.MONTANT_TTC),
        )

    def _build_declaration(self, anomaly: AnomalyType | None, filepath: str, ctx: _BuildContext) -> dict:
        if anomaly == AnomalyType.UNDECLARED_REVENUE:
            declared = round(ctx.invoice_meta.get(F.MONTANT_HT, 10000) * random.uniform(0.3, 0.6), 2)
            return self._declaration_factory.create(ctx.company, filepath, chiffre_affaires=declared)
        return self._declaration_factory.create(
            ctx.company, filepath, chiffre_affaires=ctx.invoice_meta.get(F.MONTANT_HT),
        )

    # ── Noise ─────────────────────────────────────────────────────────────

    def _apply_noise(self, filepath: str) -> None:
        if self._noise == NoiseLevel.NONE:
            return
        noisy_path = filepath.replace(".pdf", "_scan.pdf")
        self._scanner.apply_noise(filepath, noisy_path, self._noise)
        os.remove(filepath)
        os.rename(noisy_path, filepath)

    # ── Validation ────────────────────────────────────────────────────────

    def _validate_records(self, records: list[DocumentRecord]) -> None:
        for record in records:
            required = _REQUIRED_FIELDS.get(record.doc_type, [])
            missing = [f for f in required if record.fields.get(f) is None]
            if missing:
                raise ValueError(f"Document '{record.doc_type}' missing required fields: {missing}")

    # ── Getters ───────────────────────────────────────────────────────────

    def _find(self, records: list[DocumentRecord], doc_type: DocType) -> DocumentRecord | None:
        """Return the first record matching doc_type, or None."""
        return next((r for r in records if r.doc_type == doc_type), None)

    def _field(self, record: DocumentRecord | None, field_name: F):
        """Safe field access — returns None when record is absent."""
        return record.fields.get(field_name) if record else None

    # ── Metadata building ─────────────────────────────────────────────────

    def _build_metadata(
        self,
        definition: ScenarioDefinition,
        records: list[DocumentRecord],
        ctx: _BuildContext,
    ) -> ScenarioMetadata:
        invoice = self._find(records, DocType.INVOICE)
        payment = self._find(records, DocType.PAYMENT)
        declaration = self._find(records, DocType.URSSAF_DECLARATION)
        return ScenarioMetadata(
            scenario_name=definition.name,
            description=definition.description,
            risk_level=definition.risk_level,
            noise_level=str(self._noise),
            generated_documents=records,
            document_types=[r.doc_type for r in records],
            anomalies_expected=[
                self._anomaly_detail(t, records, ctx) for t in definition.anomaly_types
            ],
            anomalies_detected=[],
            financial_summary=self._build_financial_summary(invoice, payment, declaration),
            relations=self._build_relations(invoice, payment, declaration),
        )

    def _build_relations(
        self,
        invoice: DocumentRecord | None,
        payment: DocumentRecord | None,
        declaration: DocumentRecord | None,
    ) -> dict:
        relations: dict = {}
        if invoice and payment:
            relations["invoice_to_payment"] = {
                F.INVOICE_ID: self._field(invoice, F.INVOICE_ID),
                F.PAYMENT_ID: self._field(payment, F.PAYMENT_ID),
            }
        if invoice and declaration:
            relations["invoice_to_declaration"] = {
                F.INVOICE_ID: self._field(invoice, F.INVOICE_ID),
                F.PERIODE: self._field(declaration, F.PERIODE),
            }
        return relations

    def _build_financial_summary(
        self,
        invoice: DocumentRecord | None,
        payment: DocumentRecord | None,
        declaration: DocumentRecord | None,
    ) -> dict:
        summary: dict = {}
        if invoice:
            summary.update({
                F.MONTANT_HT: self._field(invoice, F.MONTANT_HT),
                F.MONTANT_TTC: self._field(invoice, F.MONTANT_TTC),
                F.MONTANT_TVA: self._field(invoice, F.MONTANT_TVA),
            })
        if payment:
            summary[F.MONTANT_PAIEMENT] = self._field(payment, F.MONTANT)
        if declaration:
            summary[F.CHIFFRE_AFFAIRES_DECLARE] = self._field(declaration, F.CHIFFRE_AFFAIRES_DECLARE)
        return summary

    # ── Anomaly detail dispatch ───────────────────────────────────────────

    def _anomaly_detail(
        self,
        anomaly_type: AnomalyType,
        records: list[DocumentRecord],
        ctx: _BuildContext,
    ) -> AnomalyDetail:
        builder = self._anomaly_builders.get(anomaly_type)
        return builder(records, ctx) if builder else AnomalyDetail(anomaly_type)

    # ── Per-anomaly detail builders ───────────────────────────────────────

    def _detail_siret_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        return AnomalyDetail(AnomalyType.SIRET_MISMATCH, {
            "bad_siret": ctx.wrong_siret_company.siret if ctx.wrong_siret_company else None,
            "expected_siret": ctx.company.siret,
        })

    def _detail_undeclared_revenue(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        declaration = self._find(records, DocType.URSSAF_DECLARATION)
        return AnomalyDetail(AnomalyType.UNDECLARED_REVENUE, {
            "expected_ca": self._field(invoice, F.MONTANT_HT),
            "declared_ca": self._field(declaration, F.CHIFFRE_AFFAIRES_DECLARE),
        })

    def _detail_tva_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        ht = self._field(invoice, F.MONTANT_HT)
        rate = self._field(invoice, F.TVA_RATE)
        expected_tva = round(ht * rate, 2) if ht and rate else None
        return AnomalyDetail(AnomalyType.TVA_MISMATCH, {
            "declared_tva": self._field(invoice, F.MONTANT_TVA),
            "expected_tva": expected_tva,
            F.MONTANT_HT: ht,
            F.TVA_RATE: rate,
        })

    def _detail_payment_amount_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        payment = self._find(records, DocType.PAYMENT)
        return AnomalyDetail(AnomalyType.PAYMENT_AMOUNT_MISMATCH, {
            "montant_facture": self._field(invoice, F.MONTANT_TTC),
            "montant_paiement": self._field(payment, F.MONTANT),
        })

    def _detail_orphan_payment(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        payment = self._find(records, DocType.PAYMENT)
        return AnomalyDetail(AnomalyType.ORPHAN_PAYMENT, {
            F.REFERENCE_FACTURE: self._field(payment, F.REFERENCE_FACTURE),
        })

    def _detail_expired_attestation(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        att = self._find(records, DocType.ATTESTATION_URSSAF)
        return AnomalyDetail(AnomalyType.EXPIRED_ATTESTATION, {
            F.DATE_EXPIRATION: self._field(att, F.DATE_EXPIRATION),
        })

    def _detail_missing_payment(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        return AnomalyDetail(AnomalyType.MISSING_PAYMENT, {
            F.INVOICE_ID: self._field(invoice, F.INVOICE_ID),
        })

    # ── Output ────────────────────────────────────────────────────────────

    def _write_metadata(self, folder: str, metadata: ScenarioMetadata) -> None:
        path = os.path.join(folder, "metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
