from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = "http://backend:8000"

st.set_page_config(page_title="IdentifAI", layout="wide", page_icon="🔍")

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🔍 IdentifAI")
st.caption("Traitement automatique de documents administratifs")

tab_upload, tab_history = st.tabs(["📤 Upload", "🕓 Historique"])

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
                progress.progress((i) / len(uploaded_files), text=f"Traitement : {f.name}")
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

            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "count": len(uploaded_files),
                "results": results,
            })

            st.subheader("Résultats")
            for r in results:
                if r["status"] == "ok":
                    with st.expander(f"✅ {r['file']} — {r['data']['pages']} page(s)"):
                        st.text_area("Texte extrait", r["data"]["text"], height=200, key=r["file"])
                else:
                    with st.expander(f"❌ {r['file']}"):
                        st.error(r["detail"])

# ── Historique ───────────────────────────────────────────────────────────────
with tab_history:
    if not st.session_state.history:
        st.info("Aucune demande pour l'instant.")
    else:
        for entry in reversed(st.session_state.history):
            ok = sum(1 for r in entry["results"] if r["status"] == "ok")
            err = entry["count"] - ok
            label = f"🕓 {entry['timestamp']} — {entry['count']} fichier(s)"
            if err:
                label += f" — ⚠️ {err} erreur(s)"
            with st.expander(label):
                for r in entry["results"]:
                    if r["status"] == "ok":
                        st.markdown(f"✅ **{r['file']}** — {r['data']['pages']} page(s)")
                        st.text_area(
                            "Texte",
                            r["data"]["text"],
                            height=150,
                            key=f"hist_{entry['timestamp']}_{r['file']}",
                        )
                    else:
                        st.markdown(f"❌ **{r['file']}** — {r['detail']}")
