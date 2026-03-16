import json
import os
import shutil
import tempfile

from dataset.generate import main


def test_generate_creates_two_folders(monkeypatch):
    """make generate must produce one clean and one errors folder."""
    outdir = tempfile.mkdtemp()
    monkeypatch.setattr(
        "sys.argv",
        ["generate", "--output", outdir, "--seed", "42"],
    )

    main()

    subdirs = [d for d in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, d))]
    assert len(subdirs) == 2
    clean = [d for d in subdirs if d.endswith("_clean")]
    errors = [d for d in subdirs if d.endswith("_errors")]
    assert len(clean) == 1
    assert len(errors) == 1

    # Each folder has 6 PDFs + metadata.json
    for d in subdirs:
        folder = os.path.join(outdir, d)
        files = os.listdir(folder)
        pdfs = [f for f in files if f.endswith(".pdf")]
        assert len(pdfs) == 6
        assert "metadata.json" in files

    shutil.rmtree(outdir)


def test_clean_metadata_has_no_errors(monkeypatch):
    outdir = tempfile.mkdtemp()
    monkeypatch.setattr("sys.argv", ["generate", "--output", outdir, "--seed", "42"])
    main()

    subdirs = os.listdir(outdir)
    clean_dir = [d for d in subdirs if d.endswith("_clean")][0]
    with open(os.path.join(outdir, clean_dir, "metadata.json")) as f:
        meta = json.load(f)

    assert meta["scenario"] == "clean"
    assert meta["errors"] == []
    assert len(meta["documents"]) == 6

    shutil.rmtree(outdir)


def test_errors_metadata_lists_injected_errors(monkeypatch):
    outdir = tempfile.mkdtemp()
    monkeypatch.setattr("sys.argv", ["generate", "--output", outdir, "--seed", "42"])
    main()

    subdirs = os.listdir(outdir)
    errors_dir = [d for d in subdirs if d.endswith("_errors")][0]
    with open(os.path.join(outdir, errors_dir, "metadata.json")) as f:
        meta = json.load(f)

    assert meta["scenario"] == "errors"
    assert "siret_mismatch_facture" in meta["errors"]
    assert "expired_urssaf" in meta["errors"]
    assert "wrong_iban" in meta["errors"]

    shutil.rmtree(outdir)
