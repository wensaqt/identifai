import json
import os
import shutil
import tempfile

from dataset.generate import main

EXPECTED_SCENARIOS = [
    "happy_path",
    "missing_payment",
    "mauvais_siret",
    "revenus_sous_declares",
    "incoherence_tva",
    "attestation_expiree",
    "paiement_sans_facture",
    "montant_paiement_incorrect",
    "annual_happy_path",
    "annual_revenus_sous_declares",
    "annual_attestation_expiree",
    "annual_incoherence_tva",
]


def _run(monkeypatch, extra_args=None):
    outdir = tempfile.mkdtemp()
    args = ["generate", "--output", outdir, "--seed", "42"]
    if extra_args:
        args.extend(extra_args)
    monkeypatch.setattr("sys.argv", args)
    main()
    return outdir


def _meta(outdir, scenario):
    with open(os.path.join(outdir, scenario, "metadata.json"), encoding="utf-8") as f:
        return json.load(f)


# ── Structural tests ──────────────────────────────────────────────────────────

def test_generate_creates_all_scenario_folders(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = sorted(d for d in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, d)))
    assert len(subdirs) == len(EXPECTED_SCENARIOS)
    for name in EXPECTED_SCENARIOS:
        assert name in subdirs, f"Missing folder: {name}"
    shutil.rmtree(outdir)


def test_all_scenarios_have_process_record_schema(monkeypatch):
    outdir = _run(monkeypatch)
    for name in EXPECTED_SCENARIOS:
        meta = _meta(outdir, name)
        assert "id" in meta
        assert "type" in meta
        assert "scenario_name" in meta
        assert "status" in meta
        assert "noise_level" in meta
        assert "documents" in meta
        assert "anomalies_expected" in meta
        assert "created_at" in meta
    shutil.rmtree(outdir)


def test_default_noise_is_none(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "happy_path")
    assert meta["noise_level"] == "none"
    shutil.rmtree(outdir)


def test_noise_flag_applies(monkeypatch):
    outdir = _run(monkeypatch, ["--noise", "medium"])
    meta = _meta(outdir, "happy_path")
    assert meta["noise_level"] == "medium"
    shutil.rmtree(outdir)


# ── Happy path ────────────────────────────────────────────────────────────────

def test_happy_path_has_all_docs_and_no_anomalies(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "happy_path")
    assert meta["scenario_name"] == "happy_path"
    assert meta["anomalies_expected"] == []
    assert meta["status"] == "valid"
    assert meta["type"] == "conformite_fournisseur"
    doc_types = {d["doc_type"] for d in meta["documents"]}
    assert "invoice" in doc_types
    assert "payment" in doc_types
    assert "urssaf_declaration" in doc_types
    shutil.rmtree(outdir)


# ── Scenario-specific tests ───────────────────────────────────────────────────

def test_missing_payment_has_no_payment_doc(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "missing_payment")
    doc_types = {d["doc_type"] for d in meta["documents"]}
    assert "payment" not in doc_types
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "missing_payment" in anomaly_types
    shutil.rmtree(outdir)


def test_missing_payment_invoice_is_paid(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "missing_payment")
    invoice = next(d for d in meta["documents"] if d["doc_type"] == "invoice")
    assert invoice["fields"]["statut_paiement"] == "paid"
    shutil.rmtree(outdir)


def test_mauvais_siret_has_mismatch(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "mauvais_siret")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "siret_mismatch" in anomaly_types
    detail = next(a for a in meta["anomalies_expected"] if a["type"] == "siret_mismatch")
    assert detail["details"]["bad_siret"] != detail["details"]["expected_siret"]
    shutil.rmtree(outdir)


def test_revenus_sous_declares(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "revenus_sous_declares")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "undeclared_revenue" in anomaly_types
    detail = next(a for a in meta["anomalies_expected"] if a["type"] == "undeclared_revenue")
    assert detail["details"]["declared_ca"] < detail["details"]["expected_ca"]
    shutil.rmtree(outdir)


def test_incoherence_tva(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "incoherence_tva")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "tva_mismatch" in anomaly_types
    detail = next(a for a in meta["anomalies_expected"] if a["type"] == "tva_mismatch")
    assert detail["details"]["declared_tva"] != detail["details"]["expected_tva"]
    shutil.rmtree(outdir)


def test_attestation_expiree(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "attestation_expiree")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "expired_attestation" in anomaly_types
    detail = next(a for a in meta["anomalies_expected"] if a["type"] == "expired_attestation")
    assert detail["details"]["date_expiration"] is not None
    shutil.rmtree(outdir)


def test_paiement_sans_facture(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "paiement_sans_facture")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "orphan_payment" in anomaly_types
    payment = next(d for d in meta["documents"] if d["doc_type"] == "payment")
    assert payment["fields"]["reference_facture"] == "F-0000-0000"
    shutil.rmtree(outdir)


def test_montant_paiement_incorrect(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "montant_paiement_incorrect")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "payment_amount_mismatch" in anomaly_types
    detail = next(a for a in meta["anomalies_expected"] if a["type"] == "payment_amount_mismatch")
    assert detail["details"]["montant_paiement"] != detail["details"]["montant_facture"]
    shutil.rmtree(outdir)


# ── Document records ──────────────────────────────────────────────────────────

def test_each_document_record_has_required_keys(monkeypatch):
    outdir = _run(monkeypatch)
    for name in EXPECTED_SCENARIOS:
        meta = _meta(outdir, name)
        for doc in meta["documents"]:
            assert "doc_id" in doc, f"{name}: missing doc_id"
            assert "doc_type" in doc, f"{name}: missing doc_type"
            assert "filename" in doc, f"{name}: missing filename"
            assert "fields" in doc, f"{name}: missing fields"
    shutil.rmtree(outdir)


# ── Status tests ──────────────────────────────────────────────────────────────

def test_error_scenarios_have_error_status(monkeypatch):
    outdir = _run(monkeypatch)
    error_scenarios = ["mauvais_siret", "attestation_expiree", "montant_paiement_incorrect", "annual_attestation_expiree"]
    for name in error_scenarios:
        meta = _meta(outdir, name)
        assert meta["status"] == "error", f"{name} should have error status"
    shutil.rmtree(outdir)


def test_warning_scenarios_have_valid_status(monkeypatch):
    outdir = _run(monkeypatch)
    # Scenarios with only warnings (no error-severity anomalies)
    warning_scenarios = [
        "missing_payment", "revenus_sous_declares", "incoherence_tva", "paiement_sans_facture",
        "annual_revenus_sous_declares", "annual_incoherence_tva",
    ]
    for name in warning_scenarios:
        meta = _meta(outdir, name)
        assert meta["status"] == "valid", f"{name} should have valid status (warnings only)"
    shutil.rmtree(outdir)


# ── Annual declaration specific tests ────────────────────────────────────────

def test_annual_happy_path(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "annual_happy_path")
    assert meta["scenario_name"] == "annual_happy_path"
    assert meta["type"] == "annual_declaration"
    assert meta["status"] == "valid"
    assert meta["anomalies_expected"] == []
    doc_types = {d["doc_type"] for d in meta["documents"]}
    assert doc_types == {"invoice", "attestation_urssaf", "urssaf_declaration"}
    assert "payment" not in doc_types
    shutil.rmtree(outdir)


def test_annual_revenus_sous_declares(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "annual_revenus_sous_declares")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "undeclared_revenue" in anomaly_types
    shutil.rmtree(outdir)


def test_annual_attestation_expiree(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "annual_attestation_expiree")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "expired_attestation" in anomaly_types
    assert meta["status"] == "error"
    shutil.rmtree(outdir)


def test_annual_incoherence_tva(monkeypatch):
    outdir = _run(monkeypatch)
    meta = _meta(outdir, "annual_incoherence_tva")
    anomaly_types = [a["type"] for a in meta["anomalies_expected"]]
    assert "tva_mismatch" in anomaly_types
    shutil.rmtree(outdir)
