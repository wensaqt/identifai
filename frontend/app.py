import json
import os
from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(
    page_title="Portail Conformité",
    layout="wide",
    page_icon="🏛️",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = None
if "active_dossier" not in st.session_state:
    st.session_state.active_dossier = None
# List of (name, bytes, mime, doc_type) — used to relaunch with corrections
if "original_files" not in st.session_state:
    st.session_state.original_files = []
# Set of doc_type strings that the backend could not find — used to highlight slots
if "missing_slot_ids" not in st.session_state:
    st.session_state.missing_slot_ids = set()

# ── Dossier métier (unique: conformité fournisseur) ────────────────────────────
# "id" must match backend DocType values exactly.
DOSSIERS = [
    {
        "id": "conformite_fournisseur",
        "titre": "Conformité fournisseur",
        "icone": "🏢",
        "description": (
            "Constituez le dossier de conformité d'un fournisseur ou sous-traitant. "
            "Le système vérifie l'identité légale, la validité des attestations, "
            "la cohérence des informations entre les documents, "
            "les paiements et les déclarations URSSAF."
        ),
        "documents": [
            {
                "id": "invoice",
                "label": "Facture",
                "hint": "Facture émise par le fournisseur",
                "obligatoire": True,
            },
            {
                "id": "siret_certificate",
                "label": "Attestation SIRET",
                "hint": "Attestation INSEE confirmant le SIRET actif",
                "obligatoire": True,
            },
            {
                "id": "urssaf_certificate",
                "label": "Attestation de vigilance URSSAF",
                "hint": "Attestation en cours de validité (moins de 6 mois)",
                "obligatoire": True,
            },
            {
                "id": "company_registration",
                "label": "Extrait Kbis",
                "hint": "Kbis de moins de 3 mois",
                "obligatoire": True,
            },
            {
                "id": "bank_account_details",
                "label": "RIB",
                "hint": "Relevé d'identité bancaire pour les paiements",
                "obligatoire": True,
            },
            {
                "id": "payment",
                "label": "Justificatif de paiement",
                "hint": "Virement, reçu ou relevé bancaire",
                "obligatoire": True,
            },
            {
                "id": "urssaf_declaration",
                "label": "Déclaration URSSAF",
                "hint": "Déclaration de chiffre d'affaires de la période concernée",
                "obligatoire": True,
            },
        ],
        "controles": [
            "Cohérence du SIRET entre la facture et les attestations",
            "Validité de l'attestation de vigilance URSSAF",
            "Correspondance entre le montant du paiement et le TTC de la facture",
            "Cohérence entre le CA déclaré et le montant HT facturé",
            "Cohérence TVA : montant TVA = HT x taux déclaré",
            "Présence de tous les documents requis",
        ],
    },
]

DOSSIER_BY_ID = {d["id"]: d for d in DOSSIERS}

# ── Labels ────────────────────────────────────────────────────────────────────
ISSUE_LABELS = {
    "siret_mismatch": ("SIRET non conforme", "Le numéro SIRET ne correspond pas entre les documents."),
    "expired_attestation": ("Attestation expirée", "L'attestation de vigilance URSSAF n'est plus valide."),
    "tva_mismatch": ("Incohérence TVA", "Le montant de TVA ne correspond pas au taux appliqué sur le HT."),
    "payment_amount_mismatch": ("Montant de paiement incorrect", "Le montant réglé ne correspond pas au TTC de la facture."),
    "orphan_payment": ("Paiement sans facture", "Le justificatif de paiement référence une facture introuvable."),
    "missing_payment": ("Paiement non justifié", "Aucun justificatif de paiement trouvé pour cette facture."),
    "undeclared_revenue": ("Chiffre d'affaires sous-déclaré", "Le CA déclaré est inférieur au montant total facturé."),
    "missing_field": ("Document incomplet", "Des informations obligatoires sont absentes du document."),
    "invalid_format": ("Format invalide", "Un champ ne respecte pas le format attendu."),
    "missing_document": ("Document manquant", "Un document requis pour cette démarche est absent du dossier."),
    "doc_type_mismatch": ("Type de document inattendu", "Le document déposé ne correspond pas au type attendu pour ce slot."),
}

DOC_TYPE_LABELS = {
    "invoice": "Facture",
    "quote": "Devis",
    "siret_certificate": "Attestation SIRET",
    "urssaf_certificate": "Attestation de vigilance URSSAF",
    "company_registration": "Extrait Kbis",
    "bank_account_details": "RIB",
    "payment": "Justificatif de paiement",
    "urssaf_declaration": "Déclaration URSSAF",
    None: "Document non reconnu",
}

FIELD_LABELS_MAP = {
    "siret": "SIRET", "siret_emetteur": "SIRET émetteur", "siren": "SIREN",
    "iban": "IBAN", "montant_ht": "Montant HT", "montant_ttc": "Montant TTC",
    "montant_tva": "Montant TVA", "montant": "Montant", "tva_rate": "Taux TVA",
    "date_emission": "Date d'émission", "date_expiration": "Date d'expiration",
    "date_paiement": "Date de paiement", "invoice_id": "N° de facture",
    "reference_facture": "Référence facture",
    "chiffre_affaires_declare": "CA déclaré", "periode": "Période",
}

STATUS_LABELS = {
    "valid": ("✅", "Conforme", "badge-ok"),
    "error": ("🚨", "Non conforme", "badge-error"),
    "cancelled": ("🗑️", "Annulé", "badge-warning"),
    "pending": ("⏳", "En cours", "badge-warning"),
}

# ── Styles CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #f8f9fb; }
    .doc-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .doc-card-required { border-left: 4px solid #3b82f6; }
    .doc-card-optional { border-left: 4px solid #94a3b8; }
    .doc-card-missing { border-left: 4px solid #ef4444; background: #fff5f5; }
    .badge-error {
        background: #fee2e2; color: #991b1b;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8em; font-weight: 600;
    }
    .badge-warning {
        background: #fef9c3; color: #92400e;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8em; font-weight: 600;
    }
    .badge-ok {
        background: #dcfce7; color: #166534;
        padding: 2px 10px; border-radius: 20px; font-size: 0.8em; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers API ───────────────────────────────────────────────────────────────

def _post_analyze(files_with_types: list[tuple]) -> tuple[dict | None, dict | None]:
    """POST /analyze. Returns (payload, error_detail) — one is always None."""
    multipart = [("files", (name, content, mime)) for name, content, mime, _ in files_with_types]
    expected_types = [doc_type for _, _, _, doc_type in files_with_types]
    try:
        resp = requests.post(
            f"{BACKEND_URL}/analyze",
            files=multipart,
            data={"doc_types": json.dumps(expected_types)},
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.json().get("detail", {"error": "unknown"})
    except Exception as e:
        return None, {"error": "connection_error", "message": str(e)}


def _store_results(payload: dict) -> None:
    st.session_state.results = {
        "documents": payload.get("documents", []),
        "issues": payload.get("anomalies", []),
        "status": payload.get("status", "valid"),
        "timestamp": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    }
    st.session_state.missing_slot_ids = set()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏛️ Portail Conformité")
    st.caption("Vérification documentaire")
    st.divider()
    st.markdown("**Démarches disponibles**")

    for dossier in DOSSIERS:
        label = f"{dossier['icone']} {dossier['titre']}"
        if st.button(label, key=f"nav_{dossier['id']}", use_container_width=True):
            st.session_state.active_dossier = dossier["id"]
            st.session_state.results = None
            st.session_state.missing_slot_ids = set()

    st.divider()
    if st.button("📋 Historique des demandes", use_container_width=True, key="nav_history"):
        st.session_state.active_dossier = "history"
        st.session_state.results = None

    st.divider()
    st.caption("Formats acceptés : PDF, JPEG, PNG — 20 Mo max par fichier")


# ── Vue Accueil ───────────────────────────────────────────────────────────────
if st.session_state.active_dossier is None:
    st.markdown("## Bienvenue sur le Portail de Conformité")
    st.markdown(
        "Ce portail vous permet de **déposer et vérifier** vos documents administratifs "
        "liés à vos fournisseurs et sous-traitants. Sélectionnez une démarche dans le menu à gauche."
    )
    st.divider()

    for dossier in DOSSIERS:
        with st.container(border=True):
            st.markdown(f"### {dossier['icone']} {dossier['titre']}")
            st.caption(dossier["description"])
            n_obligatoires = sum(1 for d in dossier["documents"] if d["obligatoire"])
            st.markdown(f"**{n_obligatoires} document(s) requis**")
            if st.button("Accéder", key=f"home_{dossier['id']}", use_container_width=True):
                st.session_state.active_dossier = dossier["id"]
                st.session_state.results = None
                st.rerun()


# ── Vue Historique ────────────────────────────────────────────────────────────
elif st.session_state.active_dossier == "history":
    st.markdown("## 📋 Historique des demandes")
    st.caption("Liste de toutes les demandes actives enregistrées.")

    try:
        resp = requests.get(f"{BACKEND_URL}/processes", timeout=10)
        processes = resp.json() if resp.status_code == 200 else []
    except Exception:
        processes = []
        st.error("Impossible de récupérer l'historique.")

    if not processes:
        st.info("Aucune demande enregistrée pour l'instant.")
    else:
        # Tri du plus récent au plus ancien
        processes = sorted(processes, key=lambda p: p.get("created_at", ""), reverse=True)
        for p in processes:
            status = p.get("status", "unknown")
            icon, label, badge_cls = STATUS_LABELS.get(status, ("❓", status, "badge-warning"))
            n_anomalies = len(p.get("anomalies", []))
            n_docs = len(p.get("documents", []))
            created = p.get("created_at", "")[:16].replace("T", " ")

            header = f"{icon} Demande `{p['id']}` — {created} — {n_docs} doc(s)"
            with st.expander(header):
                col1, col2, col3 = st.columns(3)
                col1.markdown(
                    f'<span class="{badge_cls}">{label}</span>', unsafe_allow_html=True
                )
                col2.metric("Documents", n_docs)
                col3.metric("Anomalies", n_anomalies)

                if p.get("anomalies"):
                    st.markdown("**Anomalies détectées**")
                    for a in p["anomalies"]:
                        title, detail = ISSUE_LABELS.get(a["type"], (a["type"], a.get("message", "")))
                        badge = "badge-error" if a["severity"] == "error" else "badge-warning"
                        level = "Bloquant" if a["severity"] == "error" else "À vérifier"
                        st.markdown(
                            f'<span class="{badge}">{level}</span> **{title}** — {detail}',
                            unsafe_allow_html=True,
                        )

                if p.get("documents"):
                    st.markdown("**Documents analysés**")
                    for doc in p["documents"]:
                        type_label = DOC_TYPE_LABELS.get(doc.get("doc_type"), "Inconnu")
                        st.markdown(f"- `{doc.get('filename', '?')}` — {type_label}")


# ── Vue Dossier ───────────────────────────────────────────────────────────────
else:
    dossier = DOSSIER_BY_ID[st.session_state.active_dossier]

    st.markdown(f"## {dossier['icone']} {dossier['titre']}")
    st.caption(dossier["description"])

    with st.expander("Contrôles effectués par le système"):
        for c in dossier["controles"]:
            st.markdown(f"- {c}")

    st.divider()

    # ── Formulaire ────────────────────────────────────────────────────────────
    if st.session_state.results is None:
        st.markdown("#### Documents à fournir")

        uploaded = {}
        missing_ids = st.session_state.missing_slot_ids

        with st.form(key=f"form_{dossier['id']}"):
            for doc in dossier["documents"]:
                is_missing = doc["id"] in missing_ids
                tag = "**Obligatoire**" if doc["obligatoire"] else "*Facultatif*"
                if is_missing:
                    border_class = "doc-card-missing"
                elif doc["obligatoire"]:
                    border_class = "doc-card-required"
                else:
                    border_class = "doc-card-optional"

                st.markdown(f'<div class="doc-card {border_class}">', unsafe_allow_html=True)
                col_label, col_hint = st.columns([2, 3])
                with col_label:
                    prefix = "⚠️ " if is_missing else ""
                    st.markdown(f"**{prefix}{doc['label']}** &nbsp; {tag}", unsafe_allow_html=True)
                with col_hint:
                    st.caption(doc["hint"])
                    if is_missing:
                        st.caption("🔴 Document non reconnu lors de la dernière soumission")

                f = st.file_uploader(
                    f"Déposer {doc['label']}",
                    type=["pdf", "jpg", "jpeg", "png"],
                    key=f"upload_{dossier['id']}_{doc['id']}",
                    accept_multiple_files=doc.get("multiple", False),
                    label_visibility="collapsed",
                )
                uploaded[doc["id"]] = f
                st.markdown("</div>", unsafe_allow_html=True)

            submitted = st.form_submit_button(
                "🔍 Vérifier les documents",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            files_with_types = []
            missing_required = []

            for doc in dossier["documents"]:
                f = uploaded.get(doc["id"])
                files = f if isinstance(f, list) else ([f] if f else [])

                if not files and doc["obligatoire"]:
                    missing_required.append(doc["label"])
                    continue

                for file in files:
                    if file:
                        file.seek(0)
                        files_with_types.append((file.name, file.read(), file.type, doc["id"]))

            if missing_required:
                st.error(f"Documents obligatoires manquants : {', '.join(missing_required)}")
            elif not files_with_types:
                st.error("Veuillez déposer au moins un document.")
            else:
                with st.spinner("Analyse en cours..."):
                    payload, error = _post_analyze(files_with_types)

                if payload:
                    st.session_state.original_files = files_with_types
                    _store_results(payload)
                    st.rerun()
                elif error:
                    if isinstance(error, dict) and error.get("error") == "missing_documents":
                        missing_types = error.get("missing", [])
                        missing_labels = [DOC_TYPE_LABELS.get(t, t) for t in missing_types]
                        st.error(
                            f"Documents non reconnus par le système : **{', '.join(missing_labels)}**. "
                            "Vérifiez que vous avez déposé les bons fichiers dans les bons slots."
                        )
                        st.session_state.missing_slot_ids = set(missing_types)
                    else:
                        msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                        st.error(f"Erreur : {msg}")

    # ── Résultats ─────────────────────────────────────────────────────────────
    else:
        results_data = st.session_state.results
        issues = results_data["issues"]
        documents = results_data["documents"]
        process_status = results_data.get("status", "valid")
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i for i in issues if i["severity"] == "warning"]
        issue_files = {f for i in issues for f in i.get("document_refs", [])}

        if process_status == "error" or errors:
            st.error(
                f"🚨 **{len(errors)} anomalie(s) bloquante(s) détectée(s)** — "
                "Corrigez les documents concernés et relancez l'analyse."
            )
        elif warnings:
            st.warning(
                f"⚠️ **{len(warnings)} point(s) à vérifier** — "
                "Votre dossier est traité mais requiert votre attention."
            )
        else:
            st.success(
                "✅ **Dossier conforme** — "
                "Tous les documents ont été vérifiés sans anomalie."
            )

        st.caption(f"Analyse effectuée le {results_data['timestamp']}")
        st.divider()

        col_issues, col_docs = st.columns([1, 1], gap="large")

        with col_issues:
            st.markdown("#### Résultat des contrôles")
            if not issues:
                st.markdown("Aucun point de vigilance détecté.")
            else:
                for issue in errors + warnings:
                    title, detail = ISSUE_LABELS.get(
                        issue["type"], (issue["type"], issue.get("message", ""))
                    )
                    badge = "badge-error" if issue["severity"] == "error" else "badge-warning"
                    level = "Bloquant" if issue["severity"] == "error" else "À vérifier"
                    files_str = ", ".join(issue.get("document_refs", []))
                    with st.container(border=True):
                        st.markdown(
                            f'<span class="{badge}">{level}</span> &nbsp; **{title}**',
                            unsafe_allow_html=True,
                        )
                        st.caption(detail)
                        if files_str:
                            st.caption(f"Document(s) concerné(s) : {files_str}")

        with col_docs:
            st.markdown("#### Documents analysés")

            for doc in documents:
                filename = doc.get("filename", "?")
                doc_type = doc.get("doc_type")
                fields = doc.get("fields", {})
                has_issue = filename in issue_files
                icon = "🔴" if has_issue else "✅"
                type_label = DOC_TYPE_LABELS.get(doc_type, "Document non reconnu")

                with st.expander(f"{icon} {filename} — {type_label}", expanded=has_issue):
                    if fields:
                        st.markdown("**Informations extraites**")
                        for k, v in fields.items():
                            st.markdown(f"- **{FIELD_LABELS_MAP.get(k, k)}** : `{v}`")
                    else:
                        st.caption("Aucun champ extrait.")

                    if has_issue:
                        st.divider()
                        st.markdown("**Corriger ce document**")
                        corrected = st.file_uploader(
                            "Déposer la version corrigée",
                            type=["pdf", "jpg", "jpeg", "png"],
                            key=f"fix_{filename}",
                            label_visibility="collapsed",
                        )
                        if corrected:
                            corrected.seek(0)
                            # Keep the original doc_type for this filename
                            orig_doc_type = next(
                                (dt for n, _, _, dt in st.session_state.original_files if n == filename),
                                None,
                            )
                            st.session_state.original_files = [
                                (corrected.name, corrected.read(), corrected.type, orig_doc_type)
                                if n == filename
                                else (n, c, m, dt)
                                for n, c, m, dt in st.session_state.original_files
                            ]
                            st.success(f"✅ {corrected.name} prêt à être soumis")

        st.divider()
        col_retry, col_new = st.columns(2)

        with col_retry:
            if issue_files and st.button(
                "🔄 Relancer l'analyse avec les corrections",
                type="primary",
                use_container_width=True,
            ):
                files_with_types = st.session_state.original_files
                if not files_with_types:
                    st.error("Aucun fichier disponible pour relancer l'analyse.")
                else:
                    with st.spinner("Nouvelle analyse en cours..."):
                        payload, error = _post_analyze(files_with_types)

                    if payload:
                        st.session_state.original_files = files_with_types
                        _store_results(payload)
                        st.rerun()
                    elif error:
                        msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                        st.error(f"Erreur : {msg}")

        with col_new:
            if st.button("⬅️ Nouveau dossier", use_container_width=True):
                st.session_state.results = None
                st.session_state.original_files = []
                st.session_state.missing_slot_ids = set()
                st.rerun()
