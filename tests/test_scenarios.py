"""Unit and integration tests for ScenarioDefinition, ScenarioMetadata, and ScenarioBuilder."""
import os
import shutil
import tempfile

import pytest
from faker import Faker

from dataset.builder import ScenarioBuilder
from dataset.consts import AnomalyType, DocType
from dataset.factories.company import CompanyFactory
from dataset.factories.noise import NoiseLevel
from dataset.models import AnomalyDetail, DocumentRecord, ScenarioMetadata
from dataset.scenarios import SCENARIO_BY_NAME, SCENARIOS


# ── Model unit tests ──────────────────────────────────────────────────────────

class TestAnomalyDetail:
    def test_to_dict_includes_type_and_details(self):
        a = AnomalyDetail(AnomalyType.SIRET_MISMATCH, {"bad_siret": "111", "expected_siret": "222"})
        d = a.to_dict()
        assert d["type"] == "siret_mismatch"
        assert d["details"]["bad_siret"] == "111"

    def test_empty_details_is_valid(self):
        a = AnomalyDetail(AnomalyType.MISSING_PAYMENT)
        assert a.to_dict() == {"type": "missing_payment", "details": {}}


class TestDocumentRecord:
    def test_to_dict_structure(self):
        r = DocumentRecord("abc123", DocType.INVOICE, "invoice.pdf", {"invoice_id": "F-001"})
        d = r.to_dict()
        assert d["doc_id"] == "abc123"
        assert d["doc_type"] == "invoice"
        assert d["filename"] == "invoice.pdf"
        assert d["fields"]["invoice_id"] == "F-001"


class TestScenarioMetadata:
    def _make(self, anomalies=None):
        return ScenarioMetadata(
            scenario_name="test",
            description="desc",
            risk_level="low",
            noise_level="none",
            generated_documents=[
                DocumentRecord("id1", DocType.INVOICE, "invoice.pdf", {"invoice_id": "F-001"}),
            ],
            document_types=[DocType.INVOICE],
            anomalies_expected=anomalies or [],
            anomalies_detected=[],
            financial_summary={"montant_ht": 1000.0},
            relations={},
        )

    def test_to_dict_has_all_keys(self):
        d = self._make().to_dict()
        for key in ("scenario_name", "description", "risk_level", "noise_level",
                    "generated_documents", "document_types", "anomalies_expected",
                    "anomalies_detected", "financial_summary", "relations"):
            assert key in d, f"Missing key: {key}"

    def test_anomalies_serialized(self):
        a = AnomalyDetail(AnomalyType.TVA_MISMATCH, {"declared_tva": 500.0, "expected_tva": 200.0})
        d = self._make([a]).to_dict()
        assert d["anomalies_expected"][0]["type"] == "tva_mismatch"


# ── Scenario declaration tests ────────────────────────────────────────────────

class TestScenarioDefinitions:
    def test_all_eight_scenarios_declared(self):
        names = {s.name for s in SCENARIOS}
        expected = {
            "happy_path", "missing_payment", "mauvais_siret", "revenus_sous_declares",
            "incoherence_tva", "attestation_expiree", "paiement_sans_facture",
            "montant_paiement_incorrect",
        }
        assert names == expected

    def test_scenario_by_name_lookup(self):
        assert SCENARIO_BY_NAME["happy_path"].risk_level == "low"
        assert SCENARIO_BY_NAME["mauvais_siret"].risk_level == "high"

    def test_happy_path_has_no_anomalies(self):
        assert SCENARIOS[0].anomaly_types == []

    def test_each_scenario_has_doc_specs(self):
        for s in SCENARIOS:
            assert len(s.doc_specs) >= 1, f"{s.name}: empty doc_specs"

    def test_anomaly_types_match_doc_spec_anomalies(self):
        """Every declared anomaly_type must appear in at least one doc_spec.anomaly."""
        for s in SCENARIOS:
            spec_anomalies = {spec.anomaly for spec in s.doc_specs if spec.anomaly}
            for at in s.anomaly_types:
                assert at in spec_anomalies, (
                    f"{s.name}: anomaly_type '{at}' not found in any ScenarioDocSpec"
                )


# ── Builder integration tests ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def built_scenarios():
    """Build all scenarios once into a temp dir and return {name: ScenarioMetadata}."""
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

    def test_all_doc_types_present(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["happy_path"].generated_documents}
        assert "invoice" in doc_types
        assert "payment" in doc_types
        assert "urssaf_declaration" in doc_types

    def test_invoice_to_payment_relation(self, built_scenarios):
        results, _ = built_scenarios
        rel = results["happy_path"].relations
        assert "invoice_to_payment" in rel
        assert rel["invoice_to_payment"]["invoice_id"] is not None


class TestBuilderMissingPayment:
    def test_no_payment_document(self, built_scenarios):
        results, _ = built_scenarios
        doc_types = {r.doc_type for r in results["missing_payment"].generated_documents}
        assert "payment" not in doc_types

    def test_anomaly_type_correct(self, built_scenarios):
        results, _ = built_scenarios
        types = [a.type for a in results["missing_payment"].anomalies_expected]
        assert "missing_payment" in types

    def test_invoice_is_paid(self, built_scenarios):
        results, _ = built_scenarios
        invoice = next(
            r for r in results["missing_payment"].generated_documents
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
            r for r in results["paiement_sans_facture"].generated_documents
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
