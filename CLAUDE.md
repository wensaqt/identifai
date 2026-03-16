# Spécifications – IdentifAI

## 1. Upload & Stockage

- Accepter PDF et images (JPEG, PNG)
- Stocker les fichiers bruts dans la **Raw Zone** (MongoDB GridFS ou S3-like)
- Limite de taille : 20 Mo par fichier

## 2. Classification

- Classifier chaque document parmi : `facture`, `devis`, `attestation_siret`, `attestation_urssaf`, `kbis`, `rib`
- Approche initiale : règles + mots-clés sur le texte OCR
- Évolution possible : modèle ML

## 3. OCR & Extraction

- Moteur : DocTR (modèles pré-entraînés, backend PyTorch)
- Champs à extraire :
  - SIRET (14 chiffres)
  - Numéro TVA intracommunautaire
  - Montant HT / TTC
  - Date d'émission
  - Date d'expiration (attestations)
  - IBAN / BIC (RIB)
- Stocker le texte OCR brut dans la **Clean Zone**
- Stocker les données structurées (JSON) dans la **Curated Zone**

## 4. Vérification inter-documents

- Cohérence SIRET entre facture et attestation d'un même fournisseur
- Détection d'attestations expirées (date d'expiration < date du jour)

## 5. Front-ends métiers (Streamlit)

- **CRM** : afficher fournisseur, SIRET, coordonnées bancaires
- **Conformité** : afficher statut des attestations, alertes d'expiration

## 6. Dataset

- Factures et devis générés avec Faker + ReportLab (PDF)
- 6 types de documents par entreprise, SIRET cohérent entre documents
- Bruit appliqué aux scans : rotation, flou, niveaux de gris, artefacts JPEG (light/medium/heavy)
- Métadonnées ground truth en JSON
- CLI : `python -m dataset.generate --count N --noise --seed 42`

## 7. Conteneurisation

- Un service par responsabilité (API, worker OCR, BDD, front-ends)
- Docker Compose pour l'orchestration locale
- Backend FastAPI (port 8000) avec healthcheck `/health`
- Frontend Streamlit (port 8501)

## 8. Orchestration

- Airflow pour le pipeline : ingestion → OCR → extraction → vérification → distribution
