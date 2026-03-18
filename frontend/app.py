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
if "original_files" not in st.session_state:
    # dict {filename: (name, bytes, mime)} — permet de relancer avec corrections
    st.session_state.original_files = {}

# ── Dossiers métier ───────────────────────────────────────────────────────────
# Chaque dossier correspond à un ProcessType côté backend.
# Un seul pour l'instant : conformite_fournisseur.
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
                "id": "facture",
                "label": "Facture",
                "hint": "Facture émise par le fournisseur",
                "obligatoire": True,
            },
            {
                "id": "attestation_siret",
                "label": "Attestation SIRET",
                "hint": "Attestation INSEE confirmant le SIRET actif",
                "obligatoire": True,
            },
            {
                "id": "attestation_urssaf",
                "label": "Attestation de vigilance URSSAF",
                "hint": "Attestation en cours de validité (moins de 6 mois)",
                "obligatoire": True,
            },
            {
                "id": "kbis",
                "label": "Extrait Kbis",
                "hint": "Kbis de moins de 3 mois",
                "obligatoire": True,
            },
            {
                "id": "rib",
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

# ── Labels lisibles pour les anomalies ───────────────────────────────────────
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
}

DOC_TYPE_LABELS = {
    "facture": "Facture",
    "invoice": "Facture",
    "devis": "Devis",
    "attestation_siret": "Attestation SIRET",
    "attestation_urssaf": "Attestation de vigilance URSSAF",
    "kbis": "Extrait Kbis",
    "rib": "RIB",
    "payment": "Justificatif de paiement",
    "urssaf_declaration": "Déclaration URSSAF",
    None: "Document non reconnu",
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
    .result-header {
        font-size: 1.1em; font-weight: 600; margin-bottom: 4px;
    }
    .field-row { padding: 3px 0; font-size: 0.92em; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar navigation ────────────────────────────────────────────────────────
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

    st.divider()
    st.caption("Formats acceptés : PDF, JPEG, PNG — 20 Mo max par fichier")

# ── Page principale ───────────────────────────────────────────────────────────
if st.session_state.active_dossier is None:
    # Accueil
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

else:
    dossier = DOSSIER_BY_ID[st.session_state.active_dossier]

    # ── En-tête du dossier ────────────────────────────────────────────────────
    st.markdown(f"## {dossier['icone']} {dossier['titre']}")
    st.caption(dossier["description"])

    with st.expander("Contrôles effectués par le système"):
        for c in dossier["controles"]:
            st.markdown(f"- {c}")

    st.divider()

    # ── Formulaire de dépôt ───────────────────────────────────────────────────
    if st.session_state.results is None:
        st.markdown("#### Documents à fournir")

        uploaded = {}
        with st.form(key=f"form_{dossier['id']}"):
            for doc in dossier["documents"]:
                tag = "**Obligatoire**" if doc["obligatoire"] else "*Facultatif*"
                border_class = "doc-card-required" if doc["obligatoire"] else "doc-card-optional"
                st.markdown(
                    f'<div class="doc-card {border_class}">',
                    unsafe_allow_html=True,
                )
                col_label, col_hint = st.columns([2, 3])
                with col_label:
                    st.markdown(f"**{doc['label']}** &nbsp; {tag}", unsafe_allow_html=True)
                with col_hint:
                    st.caption(doc["hint"])

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
            # Collecter tous les fichiers
            files_data = []
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
                        files_data.append((file.name, file.read(), file.type))

            if missing_required:
                st.error(f"Documents obligatoires manquants : {', '.join(missing_required)}")
            elif not files_data:
                st.error("Veuillez déposer au moins un document.")
            else:
                with st.spinner("Analyse en cours..."):
                    multipart = [("files", (name, content, mime)) for name, content, mime in files_data]
                    try:
                        resp = requests.post(f"{BACKEND_URL}/analyze", files=multipart, timeout=120)
                        if resp.status_code == 200:
                            payload = resp.json()
                            # Stocker les fichiers originaux pour permettre les corrections
                            st.session_state.original_files = {
                                name: (name, content, mime)
                                for name, content, mime in files_data
                            }
                            st.session_state.results = {
                                "documents": payload.get("documents", []),
                                "issues": payload.get("anomalies", []),
                                "status": payload.get("status", "valid"),
                                "timestamp": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                            }
                            st.rerun()
                        else:
                            st.error(f"Erreur serveur : {resp.json().get('detail', 'Erreur inconnue')}")
                    except Exception as e:
                        st.error(f"Impossible de joindre le serveur : {e}")

    # ── Résultats ─────────────────────────────────────────────────────────────
    else:
        results_data = st.session_state.results
        issues = results_data["issues"]
        documents = results_data["documents"]
        process_status = results_data.get("status", "valid")
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i for i in issues if i["severity"] == "warning"]
        issue_files = {f for i in issues for f in i.get("document_refs", [])}

        # Bandeau de statut global
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

        # Colonnes : alertes | documents
        col_issues, col_docs = st.columns([1, 1], gap="large")

        with col_issues:
            st.markdown("#### Résultat des contrôles")
            if not issues:
                st.markdown("Aucun point de vigilance détecté.")
            else:
                for issue in errors + warnings:
                    title, detail = ISSUE_LABELS.get(
                        issue["type"],
                        (issue["type"], issue.get("message", ""))
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

            FIELD_LABELS_MAP = {
                "siret": "SIRET", "siret_emetteur": "SIRET émetteur", "siren": "SIREN",
                "iban": "IBAN", "montant_ht": "Montant HT", "montant_ttc": "Montant TTC",
                "montant_tva": "Montant TVA", "montant": "Montant", "tva_rate": "Taux TVA",
                "date_emission": "Date d'émission", "date_expiration": "Date d'expiration",
                "date_paiement": "Date de paiement", "invoice_id": "N° de facture",
                "reference_facture": "Référence facture",
                "chiffre_affaires_declare": "CA déclaré", "periode": "Période",
            }

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

                    # Uploader de correction si le document a un problème
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
                            st.session_state.original_files[filename] = (
                                corrected.name, corrected.read(), corrected.type
                            )
                            st.success(f"✅ {corrected.name} prêt à être soumis")

        # Bouton relancer si des corrections ont été uploadées
        corrections_present = any(
            st.session_state.original_files.get(doc.get("filename")) and
            st.session_state.original_files[doc.get("filename")][0] != doc.get("filename")
            for doc in documents if doc.get("filename") in issue_files
        )

        st.divider()
        col_retry, col_new = st.columns(2)

        with col_retry:
            if issue_files and st.button(
                "🔄 Relancer l'analyse avec les corrections",
                type="primary",
                use_container_width=True,
            ):
                files_data = list(st.session_state.original_files.values())
                if not files_data:
                    st.error("Aucun fichier disponible pour relancer l'analyse.")
                else:
                    with st.spinner("Nouvelle analyse en cours..."):
                        multipart = [("files", t) for t in files_data]
                        try:
                            resp = requests.post(f"{BACKEND_URL}/analyze", files=multipart, timeout=120)
                            if resp.status_code == 200:
                                payload = resp.json()
                                st.session_state.original_files = {
                                    name: (name, content, mime)
                                    for name, content, mime in files_data
                                }
                                st.session_state.results = {
                                    "documents": payload.get("documents", []),
                                    "issues": payload.get("anomalies", []),
                                    "status": payload.get("status", "valid"),
                                    "timestamp": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                                }
                                st.rerun()
                            else:
                                st.error(f"Erreur : {resp.json().get('detail', 'Erreur inconnue')}")
                        except Exception as e:
                            st.error(f"Impossible de joindre le serveur : {e}")

        with col_new:
            if st.button("⬅️ Nouveau dossier", use_container_width=True):
                st.session_state.results = None
                st.session_state.original_files = {}
                st.rerun()
