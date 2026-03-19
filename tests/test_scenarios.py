"""Unit and integration tests for ScenarioDefinition, ProcessRecord, and ScenarioBuilder."""
import os
import shutil
import tempfile

import pytest
from faker import Faker

from dataset.builder import ScenarioBuilder
from dataset.consts import AnomalyType, DocType, ProcessType, Severity
from dataset.factories.company import CompanyFactory
from dataset.factories.noise import NoiseLevel
from dataset.models import AnomalyDetail, DocumentRecord, ProcessRecord
from dataset.scenarios import SCENARIO_BY_NAME, SCENARIOS


# ── Model unit tests ──────────────────────────────────────────────────────────

class TestAnomalyDetail:
    def test_to_dict_includes_type_and_details(self):
        a = AnomalyDetail(
            AnomalyType.SIRET_MISMATCH, Severity.ERROR,
            "SIRET mismatch", ["facture.pdf"],
            {"bad_siret": "111", "expected_siret": "222"},
        )
        d = a.to_dict()
        assert d["type"] == "siret_mismatch"
        assert d["severity"] == "error"
        assert d["document_refs"] == ["facture.pdf"]
        assert d["details"]["bad_siret"] == "111"

    def test_empty_details_omitted(self):
        a = AnomalyDetail(AnomalyType.MISSING_PAYMENT, Severity.WARNING, "No payment", ["invoice.pdf"])
        d = a.to_dict()
        assert "details" not in d


class TestDocumentRecord:
    def test_to_dict_structure(self):
        r = DocumentRecord("abc123", DocType.INVOICE, "invoice.pdf", {"invoice_id": "F-001"})
        d = r.to_dict()
        assert d["doc_id"] == "abc123"
        assert d["doc_type"] == "invoice"
        assert d["filename"] == "invoice.pdf"
        assert d["fields"]["invoice_id"] == "F-001"


class TestProcessRecord:
    def _make(self, anomalies=None):
        return ProcessRecord(
            id="test123",
            type=ProcessType.CONFORMITE_FOURNISSEUR,
            scenario_name="test",
            status="valid",
            noise_level="none",
            documents=[
                DocumentRecord("id1", DocType.INVOICE, "invoice.pdf", {"invoice_id": "F-001"}),
            ],
            anomalies_expected=anomalies or [],
            created_at="2026-03-18T00:00:00",
        )

    def test_to_dict_has_all_keys(self):
        d = self._make().to_dict()
        for key in ("id", "type", "scenario_name", "status", "noise_level",
                    "documents", "anomalies_expected", "created_at"):
            assert key in d, f"Missing key: {key}"

    def test_no_risk_level_or_financial_summary(self):
        d = self._make().to_dict()
        assert "risk_level" not in d
        assert "financial_summary" not in d
        assert "relations" not in d

    def test_anomalies_serialized(self):
        a = AnomalyDetail(AnomalyType.TVA_MISMATCH, Severity.WARNING, "TVA mismatch", ["invoice.pdf"],
                          {"declared_tva": 500.0, "expected_tva": 200.0})
        d = self._make([a]).to_dict()
        assert d["anomalies_expected"][0]["type"] == "tva_mismatch"


# ── Scenario declaration tests ────────────────────────────────────────────────

class TestScenarioDefinitions:
    def test_all_twelve_scenarios_declared(self):
        names = {s.name for s in SCENARIOS}
        expected = {
            "happy_path", "missing_payment", "mauvais_siret", "revenus_sous_declares",
            "incoherence_tva", "attestation_expiree", "paiement_sans_facture",
            "montant_paiement_incorrect",
            "annual_happy_path", "annual_revenus_sous_declares",
            "annual_attestation_expiree", "annual_incoherence_tva",
        }
        assert names == expected

    def test_supplier_scenarios_use_conformite_fournisseur(self):
        supplier_scenarios = [s for s in SCENARIOS if not s.name.startswith("annual_")]
        for s in supplier_scenarios:
            assert s.process_type == ProcessType.CONFORMITE_FOURNISSEUR

    def test_annual_scenarios_use_annual_declaration(self):
        annual_scenarios = [s for s in SCENARIOS if s.name.startswith("annual_")]
        assert len(annual_scenarios) == 4
        for s in annual_scenarios:
            assert s.process_type == ProcessType.ANNUAL_DECLARATION

    def test_happy_path_has_no_alterations_or_omissions(self):
        hp = SCENARIO_BY_NAME["happy_path"]
        assert hp.alterations == []
        assert hp.omitted_docs == []

    def test_missing_payment_omits_payment(self):
        mp = SCENARIO_BY_NAME["missing_payment"]
        assert DocType.PAYMENT in mp.omitted_docs

    def test_paiement_sans_facture_omits_invoice(self):
        psf = SCENARIO_BY_NAME["paiement_sans_facture"]
        assert DocType.INVOICE in psf.omitted_docs

    def test_alteration_scenarios_have_correct_anomaly(self):
        cases = {
            "mauvais_siret": AnomalyType.SIRET_MISMATCH,
            "incoherence_tva": AnomalyType.TVA_MISMATCH,
            "attestation_expiree": AnomalyType.EXPIRED_ATTESTATION,
            "montant_paiement_incorrect": AnomalyType.PAYMENT_AMOUNT_MISMATCH,
            "revenus_sous_declares": AnomalyType.UNDECLARED_REVENUE,
        }
        for name, expected_anomaly in cases.items():
            s = SCENARIO_BY_NAME[name]
            anomaly_types = {a.anomaly for a in s.alterations}
            assert expected_anomaly in anomaly_types, f"{name}: missing {expected_anomaly}"


# ── Builder integration tests ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def built_scenarios():
    """Build all scenarios once into a temp dir and return {name: ProcessRecord}."""
    fake = Faker("fr_FR")
    Faker.seed(42)
    import random
    random.seed(42)

    outdir = tempfile.mkdtemp()
    company_factory = CompanyFactory(fake)
    company = company_factory.create()
    client = company_factory.create()
    builder = ScenarioBuilder(fake, outdir, NoiseLevel.NONE)

    results = {}
    for s in SCENARIOS:
        results[s.name] = builder.build(s, company, client)

    yield results, outdir
    shutil.rmtree(outdir)


class TestBuilderHappyPath:
    def test_metadata_written_to_disk(self, built_scenarios, tmp_path):
        _, outdir = built_scenarios
        assert os.path.isfile(os.path.join(outdir, "happy_path", "metadata.json"))

    def test_no_anomalies(self, built_scenarios):
        results, _ = built_scenarios
        assert results["happy_path"].anomalies_expected == []

    def test_status_valid(self, built_scenarios):
        results, _ = built_scenarios
        assert results["happy_path"].status == "valid"

    def test_all_doc_types_present(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["happy_path"].documents}
        assert "invoice" in doc_types
        assert "payment" in doc_types
        assert "urssaf_declaration" in doc_types


class TestBuilderMissingPayment:
    def test_no_payment_document(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["missing_payment"].documents}
        assert "payment" not in doc_types

    def test_anomaly_type_correct(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["missing_payment"].anomalies_expected]
        assert "missing_payment" in types

    def test_invoice_is_paid(self, built_scenarios):
        results, _ = built_scenarios
        invoice = next(
            r for r in results["missing_payment"].documents
            if r.doc_type == "invoice"
        )
        assert invoice.fields["statut_paiement"] == "paid"


class TestBuilderMauvaisSiret:
    def test_siret_mismatch_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["mauvais_siret"].anomalies_expected]
        assert "siret_mismatch" in types

    def test_bad_siret_differs_from_expected(self, built_scenarios):
        results, _ = built_scenarios
        detail = next(
            a for a in results["mauvais_siret"].anomalies_expected
            if a.type == "siret_mismatch"
        )
        assert detail.details["bad_siret"] != detail.details["expected_siret"]

    def test_status_error(self, built_scenarios):
        results, _ = built_scenarios
        assert results["mauvais_siret"].status == "error"


class TestBuilderRevenousSousDeclares:
    def test_undeclared_revenue_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["revenus_sous_declares"].anomalies_expected]
        assert "undeclared_revenue" in types

    def test_declared_ca_less_than_invoiced(self, built_scenarios):
        results, _ = built_scenarios
        detail = next(
            a for a in results["revenus_sous_declares"].anomalies_expected
            if a.type == "undeclared_revenue"
        )
        assert detail.details["declared_ca"] < detail.details["expected_ca"]


class TestBuilderIncoherenceTva:
    def test_tva_mismatch_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["incoherence_tva"].anomalies_expected]
        assert "tva_mismatch" in types

    def test_declared_tva_differs_from_expected(self, built_scenarios):
        results, _ = built_scenarios
        detail = next(
            a for a in results["incoherence_tva"].anomalies_expected
            if a.type == "tva_mismatch"
        )
        assert detail.details["declared_tva"] != detail.details["expected_tva"]


class TestBuilderOrphanPayment:
    def test_orphan_payment_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["paiement_sans_facture"].anomalies_expected]
        assert "orphan_payment" in types

    def test_references_nonexistent_invoice(self, built_scenarios):
        results, _ = built_scenarios
        payment = next(
            r for r in results["paiement_sans_facture"].documents
            if r.doc_type == "payment"
        )
        assert payment.fields["reference_facture"] == "F-0000-0000"


class TestBuilderPaymentAmountMismatch:
    def test_payment_amount_mismatch_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["montant_paiement_incorrect"].anomalies_expected]
        assert "payment_amount_mismatch" in types

    def test_payment_amount_differs_from_ttc(self, built_scenarios):
        results, _ = built_scenarios
        detail = next(
            a for a in results["montant_paiement_incorrect"].anomalies_expected
            if a.type == "payment_amount_mismatch"
        )
        assert detail.details["montant_paiement"] != detail.details["montant_facture"]


# ── Annual declaration builder tests ─────────────────────────────────────────

class TestBuilderAnnualHappyPath:
    def test_status_valid(self, built_scenarios):
        results, _ = built_scenarios
        assert results["annual_happy_path"].status == "valid"

    def test_no_anomalies(self, built_scenarios):
        results, _ = built_scenarios
        assert results["annual_happy_path"].anomalies_expected == []

    def test_three_doc_types(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["annual_happy_path"].documents}
        assert doc_types == {"invoice", "attestation_urssaf", "urssaf_declaration"}

    def test_no_payment_doc(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["annual_happy_path"].documents}
        assert "payment" not in doc_types


class TestBuilderAnnualRevenousSousDeclares:
    def test_undeclared_revenue_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["annual_revenus_sous_declares"].anomalies_expected]
        assert "undeclared_revenue" in types

    def test_status_valid(self, built_scenarios):
        results, _ = built_scenarios
        assert results["annual_revenus_sous_declares"].status == "valid"


class TestBuilderAnnualAttestationExpiree:
    def test_expired_attestation_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["annual_attestation_expiree"].anomalies_expected]
        assert "expired_attestation" in types

    def test_status_error(self, built_scenarios):
        results, _ = built_scenarios
        assert results["annual_attestation_expiree"].status == "error"


class TestBuilderAnnualIncoherenceTva:
    def test_tva_mismatch_anomaly(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["annual_incoherence_tva"].anomalies_expected]
        assert "tva_mismatch" in types

    def test_status_valid(self, built_scenarios):
        results, _ = built_scenarios
        assert results["annual_incoherence_tva"].status == "valid"


class TestBuilderValidation:
    def test_missing_required_field_raises(self, tmp_path):
        """Builder must raise ValueError if a factory produces incomplete data."""
        from unittest.mock import patch
        from dataset.builder import ScenarioBuilder as SB
        from dataset.scenarios import SCENARIO_BY_NAME

        fake = Faker("fr_FR")
        Faker.seed(0)
        builder = SB(fake, str(tmp_path), NoiseLevel.NONE)
        company = CompanyFactory(fake).create()
        client = CompanyFactory(fake).create()

        # Patch invoice factory to return a dict missing required fields
        bad_meta = {"type": "invoice", "siret_emetteur": "12345678901234"}
        with patch.object(builder._invoice_factory, "create", return_value=bad_meta):
            with pytest.raises(ValueError, match="missing required fields"):
                builder.build(SCENARIO_BY_NAME["happy_path"], company, client)
