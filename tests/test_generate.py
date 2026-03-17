import json
import os
import shutil
import tempfile

from dataset.generate import main

EXPECTED_SCENARIOS = [
    "_clean",
    "_ERR_siret_mismatch",
    "_ERR_attestation_expired",
    "_ERR_all",
    "_ERR_missing_fields_facture",
    "_ERR_missing_fields_rib",
    "_ERR_missing_fields_urssaf",
]


def _run(monkeypatch):
    outdir = tempfile.mkdtemp()
    monkeypatch.setattr("sys.argv", ["generate", "--output", outdir, "--seed", "42"])
    main()
    return outdir


def test_generate_creates_all_scenario_folders(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = [d for d in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, d))]
    assert len(subdirs) == len(EXPECTED_SCENARIOS)
    for suffix in EXPECTED_SCENARIOS:
        assert any(d.endswith(suffix) for d in subdirs), f"Missing folder ending with {suffix}"
    shutil.rmtree(outdir)


def test_clean_metadata_has_no_errors(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = os.listdir(outdir)
    clean_dir = [d for d in subdirs if d.endswith("_clean")][0]
    with open(os.path.join(outdir, clean_dir, "metadata.json")) as f:
        meta = json.load(f)
    assert meta["scenario"] == "clean"
    assert meta["errors"] == []
    assert len(meta["documents"]) == 6
    shutil.rmtree(outdir)


def test_errors_metadata_lists_injected_errors(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = os.listdir(outdir)
    err_dir = [d for d in subdirs if d.endswith("_ERR_all")][0]
    with open(os.path.join(outdir, err_dir, "metadata.json")) as f:
        meta = json.load(f)
    assert meta["scenario"] == "ERR_all"
    assert "siret_mismatch" in meta["expected_alerts"]
    assert "expired_attestation" in meta["expected_alerts"]
    shutil.rmtree(outdir)


def test_missing_fields_scenarios_have_metadata(monkeypatch):
    outdir = _run(monkeypatch)
    subdirs = os.listdir(outdir)
    for suffix in ["_ERR_missing_fields_facture", "_ERR_missing_fields_rib", "_ERR_missing_fields_urssaf"]:
        d = [x for x in subdirs if x.endswith(suffix)][0]
        with open(os.path.join(outdir, d, "metadata.json")) as f:
            meta = json.load(f)
        assert "missing_fields" in meta["expected_alerts"]
        assert len(meta["missing"]) > 0
    shutil.rmtree(outdir)
