from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from faker import Faker

from .consts import (
    ANOMALY_SEVERITY,
    PROCESS_REQUIRED_DOCS,
    AnomalyType,
    DocType,
    FieldName as F,
    ProcessType,
    Severity,
)
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
    ProcessRecord,
    ScenarioDefinition,
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
            AnomalyType.MISSING_DOCUMENT: self._detail_missing_document,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def build(
        self,
        definition: ScenarioDefinition,
        company: CompanyIdentity,
        client: CompanyIdentity,
    ) -> ProcessRecord:
        """Generate all documents, validate them, and write metadata.json."""
        folder = os.path.join(self._output_dir, definition.name)
        os.makedirs(folder, exist_ok=True)

        ctx = self._init_context(definition, company, client)
        doc_types = self._resolve_doc_types(definition)
        alteration_map = self._build_alteration_map(definition)

        records = [
            self._build_doc(dt, alteration_map.get(dt), folder, ctx)
            for dt in doc_types
        ]
        self._validate_records(records)

        process_record = self._build_process_record(definition, records, ctx)
        self._write_metadata(folder, process_record)
        return process_record

    # ── Context ───────────────────────────────────────────────────────────

    def _init_context(
        self,
        definition: ScenarioDefinition,
        company: CompanyIdentity,
        client: CompanyIdentity,
    ) -> _BuildContext:
        alteration_anomalies = {a.anomaly for a in definition.alterations}
        omitted = set(definition.omitted_docs)
        required = PROCESS_REQUIRED_DOCS.get(ProcessType(definition.process_type), frozenset())
        ctx = _BuildContext(
            company=company,
            client=client,
            has_payment=DocType.PAYMENT in required and DocType.PAYMENT not in omitted,
        )
        if AnomalyType.SIRET_MISMATCH in alteration_anomalies:
            ctx.wrong_siret_company = self._company_factory.with_wrong_siret(company)
        return ctx

    # ── Document resolution ────────────────────────────────────────────────

    def _resolve_doc_types(self, definition: ScenarioDefinition) -> list[DocType]:
        """Get required doc types for the process, minus omitted ones."""
        required = PROCESS_REQUIRED_DOCS.get(
            ProcessType(definition.process_type), frozenset(),
        )
        omitted = set(definition.omitted_docs)
        return [dt for dt in sorted(required) if dt not in omitted]

    def _build_alteration_map(self, definition: ScenarioDefinition) -> dict[DocType, AnomalyType]:
        """Build a lookup: doc_type → anomaly to inject."""
        return {a.doc_type: a.anomaly for a in definition.alterations}

    # ── Document building ─────────────────────────────────────────────────

    def _build_doc(
        self, doc_type: DocType, anomaly: AnomalyType | None,
        folder: str, ctx: _BuildContext,
    ) -> DocumentRecord:
        filepath = os.path.join(folder, f"{doc_type}.pdf")
        handler = self._factory_handlers.get(doc_type)
        if handler is None:
            raise ValueError(f"Unknown doc_type: {doc_type!r}")
        raw = handler(anomaly, filepath, ctx)
        self._apply_noise(filepath)
        fields = {k: v for k, v in raw.items() if k not in ("type", "filename", "noise_level")}
        return DocumentRecord(
            doc_id=uuid.uuid4().hex[:8],
            doc_type=doc_type,
            filename=f"{doc_type}.pdf",
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
        ctx.invoice_meta.update(meta)
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
        return next((r for r in records if r.doc_type == doc_type), None)

    def _field(self, record: DocumentRecord | None, field_name: F):
        return record.fields.get(field_name) if record else None

    # ── Process record building ───────────────────────────────────────────

    def _build_process_record(
        self,
        definition: ScenarioDefinition,
        records: list[DocumentRecord],
        ctx: _BuildContext,
    ) -> ProcessRecord:
        anomalies = self._build_expected_anomalies(definition, records, ctx)
        status = self._compute_status(anomalies)
        return ProcessRecord(
            id=uuid.uuid4().hex[:8],
            type=definition.process_type,
            scenario_name=definition.name,
            status=status,
            noise_level=str(self._noise),
            documents=records,
            anomalies_expected=anomalies,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    def _build_expected_anomalies(
        self,
        definition: ScenarioDefinition,
        records: list[DocumentRecord],
        ctx: _BuildContext,
    ) -> list[AnomalyDetail]:
        anomalies: list[AnomalyDetail] = []
        alteration_anomalies = {a.anomaly for a in definition.alterations}

        # Anomalies from alterations
        for alteration in definition.alterations:
            anomalies.append(self._anomaly_detail(alteration.anomaly, records, ctx))

        # Anomalies from omitted docs — skip if already covered by an alteration
        for doc_type in definition.omitted_docs:
            if doc_type == DocType.PAYMENT and AnomalyType.MISSING_PAYMENT in alteration_anomalies:
                continue
            if doc_type == DocType.INVOICE and AnomalyType.ORPHAN_PAYMENT in alteration_anomalies:
                continue
            anomalies.append(self._detail_missing_document_for(doc_type))

        return anomalies

    def _compute_status(self, anomalies: list[AnomalyDetail]) -> str:
        has_error = any(a.severity == Severity.ERROR for a in anomalies)
        return "error" if has_error else "valid"

    # ── Anomaly detail dispatch ───────────────────────────────────────────

    def _anomaly_detail(
        self,
        anomaly_type: AnomalyType,
        records: list[DocumentRecord],
        ctx: _BuildContext,
    ) -> AnomalyDetail:
        builder = self._anomaly_builders.get(anomaly_type)
        if builder:
            return builder(records, ctx)
        severity = ANOMALY_SEVERITY.get(anomaly_type, Severity.WARNING)
        return AnomalyDetail(anomaly_type, severity, str(anomaly_type), [])

    # ── Per-anomaly detail builders ───────────────────────────────────────

    def _detail_siret_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        att_siret = self._find(records, DocType.ATTESTATION_SIRET)
        refs = [r.filename for r in [invoice, att_siret] if r]
        return AnomalyDetail(
            AnomalyType.SIRET_MISMATCH, Severity.ERROR,
            "SIRET incohérent entre facture et attestations",
            refs,
            details={
                "bad_siret": ctx.wrong_siret_company.siret if ctx.wrong_siret_company else None,
                "expected_siret": ctx.company.siret,
            },
        )

    def _detail_undeclared_revenue(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        declaration = self._find(records, DocType.URSSAF_DECLARATION)
        refs = [r.filename for r in [declaration] if r]
        return AnomalyDetail(
            AnomalyType.UNDECLARED_REVENUE, Severity.WARNING,
            "CA déclaré inférieur à 90% du HT facturé",
            refs,
            details={
                "expected_ca": self._field(invoice, F.MONTANT_HT),
                "declared_ca": self._field(declaration, F.CHIFFRE_AFFAIRES_DECLARE),
            },
        )

    def _detail_tva_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        ht = self._field(invoice, F.MONTANT_HT)
        rate = self._field(invoice, F.TVA_RATE)
        expected_tva = round(ht * rate, 2) if ht and rate else None
        refs = [invoice.filename] if invoice else []
        return AnomalyDetail(
            AnomalyType.TVA_MISMATCH, Severity.WARNING,
            "TVA incohérente",
            refs,
            details={
                "declared_tva": self._field(invoice, F.MONTANT_TVA),
                "expected_tva": expected_tva,
            },
        )

    def _detail_payment_amount_mismatch(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        payment = self._find(records, DocType.PAYMENT)
        refs = [r.filename for r in [payment, invoice] if r]
        return AnomalyDetail(
            AnomalyType.PAYMENT_AMOUNT_MISMATCH, Severity.ERROR,
            "Montant du paiement différent du TTC facture",
            refs,
            details={
                "montant_facture": self._field(invoice, F.MONTANT_TTC),
                "montant_paiement": self._field(payment, F.MONTANT),
            },
        )

    def _detail_orphan_payment(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        payment = self._find(records, DocType.PAYMENT)
        refs = [payment.filename] if payment else []
        return AnomalyDetail(
            AnomalyType.ORPHAN_PAYMENT, Severity.WARNING,
            "Paiement référence une facture inexistante",
            refs,
            details={
                F.REFERENCE_FACTURE: self._field(payment, F.REFERENCE_FACTURE),
            },
        )

    def _detail_expired_attestation(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        att = self._find(records, DocType.ATTESTATION_URSSAF)
        refs = [att.filename] if att else []
        return AnomalyDetail(
            AnomalyType.EXPIRED_ATTESTATION, Severity.ERROR,
            "Attestation URSSAF expirée",
            refs,
            details={
                F.DATE_EXPIRATION: self._field(att, F.DATE_EXPIRATION),
            },
        )

    def _detail_missing_payment(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        invoice = self._find(records, DocType.INVOICE)
        refs = [invoice.filename] if invoice else []
        return AnomalyDetail(
            AnomalyType.MISSING_PAYMENT, Severity.WARNING,
            "Aucun paiement trouvé pour la facture",
            refs,
            details={
                F.INVOICE_ID: self._field(invoice, F.INVOICE_ID),
            },
        )

    def _detail_missing_document(self, records: list[DocumentRecord], ctx: _BuildContext) -> AnomalyDetail:
        return AnomalyDetail(
            AnomalyType.MISSING_DOCUMENT, Severity.ERROR,
            "Document manquant",
            [],
        )

    def _detail_missing_document_for(self, doc_type: DocType) -> AnomalyDetail:
        return AnomalyDetail(
            AnomalyType.MISSING_DOCUMENT, Severity.ERROR,
            f"Document manquant : {doc_type}",
            [],
        )

    # ── Output ────────────────────────────────────────────────────────────

    def _write_metadata(self, folder: str, process_record: ProcessRecord) -> None:
        path = os.path.join(folder, "metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(process_record.to_dict(), f, ensure_ascii=False, indent=2)
