import os
from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="IdentifAI", layout="wide", page_icon="🔍")

if "history" not in st.session_state:
    st.session_state.history = []
if "last_results" not in st.session_state:
    st.session_state.last_results = None

st.title("🔍 IdentifAI")
st.caption("Traitement automatique de documents administratifs")

tab_upload, tab_history = st.tabs(["📤 Upload", "🕓 Historique"])

DOC_TYPE_LABELS = {
    "facture": "Facture",
    "devis": "Devis",
    "attestation_siret": "Attestation SIRET",
    "attestation_urssaf": "Attestation URSSAF",
    "kbis": "Kbis",
    "rib": "RIB",
    None: "Inconnu",
}

FIELD_LABELS = {
    "siret": "SIRET",
    "siret_client": "SIRET client",
    "tva": "TVA",
    "iban": "IBAN",
    "bic": "BIC",
    "montant_ht": "Montant HT",
    "montant_ttc": "Montant TTC",
    "date_emission": "Date d'émission",
    "date_expiration": "Date d'expiration",
}

# Champs obligatoires par type de document
REQUIRED_FIELDS = {
    "facture": ["siret", "montant_ht", "montant_ttc", "date_emission"],
    "devis": ["siret", "montant_ht", "date_emission"],
    "attestation_urssaf": ["siret", "date_expiration"],
    "attestation_siret": ["siret"],
    "kbis": ["siret"],
    "rib": ["iban"],
}


def _fields_in_issue(filename: str, issues: list[dict]) -> set[str]:
    """Retourne les noms de champs problématiques pour un fichier donné."""
    flagged = set()
    for issue in issues:
        if filename not in issue.get("files", []):
            continue
        if issue["type"] == "siret_mismatch":
            flagged.add("siret")
        elif issue["type"] == "expired_attestation":
            flagged.add("date_expiration")
        elif issue["type"] == "missing_fields":
            # extraire les champs du message "Champs manquants (facture) : siret, montant_ht"
            msg = issue["message"]
            if ":" in msg:
                for f in msg.split(":")[1].split(","):
                    flagged.add(f.strip())
    return flagged


def _render_issues(issues: list[dict]):
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    for issue in errors:
        st.error(f"🚨 {issue['message']}  \n*Fichiers : {', '.join(issue['files'])}*")
    for issue in warnings:
        st.warning(f"⚠️ {issue['message']}  \n*Fichiers : {', '.join(issue['files'])}*")


def _render_result_content(r: dict, key_prefix: str, issues: list[dict]):
    if r["status"] != "ok":
        st.error(r["detail"])
        return

    data = r["data"]
    fields = data.get("fields", {})
    doc_type = data.get("doc_type")
    flagged = _fields_in_issue(r["file"], issues)
    required = REQUIRED_FIELDS.get(doc_type, [])
    missing = [f for f in required if f not in fields]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Champs extraits**")
        if fields:
            for k, v in fields.items():
                label = FIELD_LABELS.get(k, k)
                if k in flagged:
                    st.markdown(f"- 🔴 **{label}** : `{v}` ← problème détecté")
                else:
                    st.markdown(f"- ✅ **{label}** : `{v}`")
        else:
            st.caption("Aucun champ extrait")

        if missing:
            st.markdown("**Champs manquants**")
            for f in missing:
                st.markdown(f"- 🔴 **{FIELD_LABELS.get(f, f)}** : non trouvé")

    with col2:
        st.markdown("**Texte OCR brut**")
        st.text_area("", data["text"], height=200, key=f"{key_prefix}_{r['file']}_{id(r)}")


def _render_result(r: dict, key_prefix: str, issues: list[dict], nested: bool = False):
    data = r.get("data", {})
    doc_type = data.get("doc_type") if r["status"] == "ok" else None
    label = DOC_TYPE_LABELS.get(doc_type, "Inconnu")
    pages = data.get("pages", 0) if r["status"] == "ok" else 0
    flagged = _fields_in_issue(r["file"], issues)
    icon = "🔴" if flagged else ("✅" if r["status"] == "ok" else "❌")
    title = f"{icon} {r['file']} — {label} — {pages} page(s)" if r["status"] == "ok" else f"{icon} {r['file']}"

    if nested:
        st.markdown(f"**{title}**")
        _render_result_content(r, key_prefix, issues)
        st.divider()
    else:
        with st.expander(title):
            _render_result_content(r, key_prefix, issues)


# ── Upload ──────────────────────────────────────────────────────────────────
with tab_upload:
    uploaded_files = st.file_uploader(
        "Déposez vos documents (PDF, JPEG, PNG — max 20 Mo chacun)",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.subheader(f"{len(uploaded_files)} fichier(s) sélectionné(s)")

        cols = st.columns(min(len(uploaded_files), 3))
        for i, f in enumerate(uploaded_files):
            with cols[i % 3]:
                if f.type == "application/pdf":
                    st.markdown(f"📄 **{f.name}**")
                    st.caption(f"{f.size / 1024:.1f} Ko")
                else:
                    st.image(f, caption=f.name, use_container_width=True)
                    st.caption(f"{f.size / 1024:.1f} Ko")

        st.divider()

        if st.button("🚀 Lancer l'OCR", type="primary"):
            results = []
            progress = st.progress(0, text="Traitement en cours...")

            for i, f in enumerate(uploaded_files):
                progress.progress(i / len(uploaded_files), text=f"Traitement : {f.name}")
                f.seek(0)
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/ocr",
                        files={"file": (f.name, f.read(), f.type)},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({"file": f.name, "status": "ok", "data": data})
                    else:
                        results.append({"file": f.name, "status": "error", "detail": resp.json().get("detail", "Erreur inconnue")})
                except Exception as e:
                    results.append({"file": f.name, "status": "error", "detail": str(e)})

            progress.progress(1.0, text="Terminé ✅")

            ok_docs = [r["data"] for r in results if r["status"] == "ok"]
            issues = []
            if len(ok_docs) > 1:
                try:
                    verify_resp = requests.post(f"{BACKEND_URL}/verify", json=ok_docs, timeout=10)
                    if verify_resp.status_code == 200:
                        issues = verify_resp.json().get("issues", [])
                except Exception:
                    pass

            entry = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "count": len(uploaded_files),
                "results": results,
                "issues": issues,
            }
            st.session_state.history.append(entry)
            st.session_state.last_results = entry

        if st.session_state.last_results:
            entry = st.session_state.last_results
            results = entry["results"]
            issues = entry["issues"]

            if issues:
                st.subheader("⚠️ Alertes")
                _render_issues(issues)
            else:
                st.success("✅ Aucune incohérence détectée")

            run_key = entry["timestamp"].replace("/", "").replace(":", "").replace(" ", "")
            st.subheader("Résultats")
            for r in results:
                _render_result(r, key_prefix=f"upload_{run_key}", issues=issues)


# ── Historique ───────────────────────────────────────────────────────────────
with tab_history:
    if not st.session_state.history:
        st.info("Aucune demande pour l'instant.")
    else:
        for entry in reversed(st.session_state.history):
            ok = sum(1 for r in entry["results"] if r["status"] == "ok")
            err = entry["count"] - ok
            n_issues = len(entry.get("issues", []))
            label = f"🕓 {entry['timestamp']} — {entry['count']} fichier(s)"
            if err:
                label += f" — ❌ {err} erreur(s)"
            if n_issues:
                label += f" — ⚠️ {n_issues} alerte(s)"
            with st.expander(label):
                if entry.get("issues"):
                    _render_issues(entry["issues"])
                    st.divider()
                for r in entry["results"]:
                    _render_result(r, key_prefix=f"hist_{entry['timestamp']}", issues=entry.get("issues", []), nested=True)
