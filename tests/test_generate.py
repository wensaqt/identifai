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
]


def _run(monkeypatch):
    outdir = tempfile.mkdtemp()
    monkeypatch.setattr("sys.argv", ["generate", "--output", outdir, "--seed", "42"])
    main()
    return outdir


def test_generate_creates_all_scenario_folders(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = sorted(d for d in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, d)))
    assert len(subdirs) == len(EXPECTED_SCENARIOS)
    for name in EXPECTED_SCENARIOS:
        assert name in subdirs, f"Missing folder: {name}"
    shutil.rmtree(outdir)


def test_happy_path_has_all_docs_and_no_anomalies(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "happy_path", "metadata.json")) as f:
        meta = json.load(f)
    assert meta["scenario_type"] == "happy_path"
    assert meta["expected_anomalies"] == []
    assert meta["risk_level"] == "low"
    doc_types = {d["type"] for d in meta["documents"]}
    assert "invoice" in doc_types
    assert "payment" in doc_types
    assert "urssaf_declaration" in doc_types
    shutil.rmtree(outdir)


def test_missing_payment_has_no_payment_doc(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "missing_payment", "metadata.json")) as f:
        meta = json.load(f)
    doc_types = {d["type"] for d in meta["documents"]}
    assert "payment" not in doc_types
    assert "missing_payment" in meta["expected_anomalies"]
    shutil.rmtree(outdir)


def test_mauvais_siret_has_mismatch(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "mauvais_siret", "metadata.json")) as f:
        meta = json.load(f)
    assert "siret_mismatch" in meta["expected_anomalies"]
    assert meta["bad_siret"] != meta["expected_siret"]
    shutil.rmtree(outdir)


def test_revenus_sous_declares(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "revenus_sous_declares", "metadata.json")) as f:
        meta = json.load(f)
    assert "undeclared_revenue" in meta["expected_anomalies"]
    # Check declaration CA < invoice HT
    invoice = next(d for d in meta["documents"] if d["type"] == "invoice")
    decl = next(d for d in meta["documents"] if d["type"] == "urssaf_declaration")
    assert decl["chiffre_affaires_declare"] < invoice["montant_ht"]
    shutil.rmtree(outdir)


def test_incoherence_tva(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "incoherence_tva", "metadata.json")) as f:
        meta = json.load(f)
    assert "tva_mismatch" in meta["expected_anomalies"]
    invoice = next(d for d in meta["documents"] if d["type"] == "invoice")
    expected_tva = round(invoice["montant_ht"] * invoice["tva_rate"], 2)
    assert invoice["montant_tva"] != expected_tva
    shutil.rmtree(outdir)


def test_attestation_expiree(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "attestation_expiree", "metadata.json")) as f:
        meta = json.load(f)
    assert "expired_attestation" in meta["expected_anomalies"]
    shutil.rmtree(outdir)


def test_paiement_sans_facture(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "paiement_sans_facture", "metadata.json")) as f:
        meta = json.load(f)
    assert "orphan_payment" in meta["expected_anomalies"]
    payment = next(d for d in meta["documents"] if d["type"] == "payment")
    assert payment["reference_facture"] == "F-0000-0000"
    doc_types = {d["type"] for d in meta["documents"]}
    assert "invoice" not in doc_types
    shutil.rmtree(outdir)


def test_montant_paiement_incorrect(monkeypatch):
    outdir = _run(monkeypatch)
    with open(os.path.join(outdir, "montant_paiement_incorrect", "metadata.json")) as f:
        meta = json.load(f)
    assert "payment_amount_mismatch" in meta["expected_anomalies"]
    invoice = next(d for d in meta["documents"] if d["type"] == "invoice")
    payment = next(d for d in meta["documents"] if d["type"] == "payment")
    assert payment["montant"] != invoice["montant_ttc"]
    shutil.rmtree(outdir)


def test_all_scenarios_have_metadata_schema(monkeypatch):
    """Every scenario metadata must have the 4 required fields."""
    outdir = _run(monkeypatch)
    for name in EXPECTED_SCENARIOS:
        with open(os.path.join(outdir, name, "metadata.json")) as f:
            meta = json.load(f)
        assert "scenario_type" in meta, f"{name} missing scenario_type"
        assert "description" in meta, f"{name} missing description"
        assert "expected_anomalies" in meta, f"{name} missing expected_anomalies"
        assert "risk_level" in meta, f"{name} missing risk_level"
    shutil.rmtree(outdir)
