# Spécifications – IdentifAI

## 1. Architecture générale

```
POST /analyze (multi-fichiers)
  OCR (DocTR) → Classification → Extraction (type-aware) → Validation → Vérification inter-documents

POST /ocr (fichier unique)
  OCR → Classification → Extraction → Validation

POST /verify (batch pré-traité)
  Vérification inter-documents
```

## 2. Upload & Stockage

- Accepter PDF et images (JPEG, PNG)
- Limite de taille : 20 Mo par fichier
- Stocker les fichiers bruts dans la **Raw Zone** (MongoDB GridFS ou S3-like)
- Stocker le texte OCR brut dans la **Clean Zone**
- Stocker les données structurées (JSON) dans la **Curated Zone**

## 3. Classification

- 8 types de documents : `facture`, `devis`, `attestation_siret`, `attestation_urssaf`, `kbis`, `rib`, `payment`, `urssaf_declaration`
- Approche : règles ordonnées + mots-clés regex sur le texte OCR (`backend/classifier.py`)
- Les types sont définis dans l'enum `DocType` (`backend/consts/doc_types.py`)
- Évolution possible : modèle ML

## 4. OCR & Extraction

- Moteur : DocTR (db_resnet50 + crnn_vgg16_bn, backend PyTorch)
- Extraction type-aware : chaque type de document a ses propres getters
- Champs extraits selon le type (voir `backend/models.py` pour les champs requis par type) :
  - **Facture** : invoice_id, siret_emetteur, montant_ht, montant_ttc, montant_tva, tva_rate, date_emission, date_prestation
  - **Devis** : siret_emetteur, montant_ht, date_emission, date_validite
  - **Attestation SIRET** : siret, siren, date_inscription
  - **Attestation URSSAF** : siret, date_expiration, date_delivrance
  - **Kbis** : siret, siren
  - **RIB** : iban, bic
  - **Paiement** : payment_id, montant, date_paiement, reference_facture, methode
  - **Déclaration URSSAF** : siret, periode, chiffre_affaires_declare, date_declaration
- Les noms de champs sont dans l'enum `FieldName` (`backend/consts/fields.py`)
- Les regex d'extraction/validation sont dans `backend/consts/patterns.py`

## 5. Validation (3 couches)

### Couche 1 — Complétude (`backend/validator.py`)
Vérifie que tous les `REQUIRED_FIELDS` du type classifié sont présents.

### Couche 2 — Format (`backend/validator.py`)
Validation regex des champs : SIRET (14 chiffres), SIREN (9), TVA (FR format), IBAN, BIC, dates, montants, période.

### Couche 3 — Vérification inter-documents (`backend/verifier.py`)
| Check | Sévérité |
|-------|----------|
| Cohérence SIRET facture ↔ attestations | error |
| Attestation URSSAF expirée | error |
| Montant paiement ≠ TTC facture | error |
| TVA ≠ HT × taux | warning |
| Paiement orphelin (facture inexistante) | warning |
| Facture sans paiement associé | warning |
| CA déclaré < 90% du HT facturé | warning |

## 6. Front-ends métiers (Streamlit)

- **CRM** : afficher fournisseur, SIRET, coordonnées bancaires
- **Conformité** : afficher statut des attestations, alertes d'expiration

## 7. Dataset

### Structure
```
dataset/
├── factories/
│   ├── company.py    → CompanyFactory + CompanyIdentity (dataclass)
│   ├── documents.py  → InvoiceFactory, DevisFactory, AttestationSiretFactory, etc.
│   └── noise.py      → ScanSimulator + NoiseLevel (enum)
├── generate.py       → ScenarioGenerator (class)
├── company.py        → shims rétro-compatibles
├── documents.py      → shims rétro-compatibles
└── noise.py          → shims rétro-compatibles
```

### 8 scénarios métier
| Dossier | Anomalies | Risque |
|---------|-----------|--------|
| `happy_path/` | aucune | low |
| `missing_payment/` | missing_payment | medium |
| `mauvais_siret/` | siret_mismatch | high |
| `revenus_sous_declares/` | undeclared_revenue | high |
| `incoherence_tva/` | tva_mismatch | medium |
| `attestation_expiree/` | expired_attestation | high |
| `paiement_sans_facture/` | orphan_payment | medium |
| `montant_paiement_incorrect/` | payment_amount_mismatch | medium |

### CLI
```bash
make generate              # PDFs clean (sans noise)
make generate-noisy        # PDFs avec noise medium
python -m dataset.generate --noise heavy --seed 42
```

### Bruit de scan (ScanSimulator)
- `none` : PDF propres (par défaut)
- `light` : rotation ±2°, flou 0.5, JPEG 80%
- `medium` : rotation ±3°, flou 1.0, JPEG 60%
- `heavy` : rotation ±5°, flou 1.5, JPEG 40%

## 8. Conteneurisation

```yaml
services:
  backend:   # FastAPI (port 8000), healthcheck /health
  frontend:  # Streamlit (port 8501)
  test:      # pytest (profile: test)
  dataset:   # Génération dataset (profile: dataset)
```

### Makefile
```
make up           # docker compose up --build -d
make down         # docker compose down
make test         # pytest dans Docker
make lint         # ruff dans Docker
make generate     # génération clean
make generate-noisy
make logs
make clean
```

## 9. Conventions de code

### Principes
- **SRP** : une fonction = une responsabilité. Si une fonction fait plus d'une chose, la découper.
- **Pas d'imbrication** : jamais plus d'un niveau de `if` ou `for`. Extraire dans des méthodes privées.
- **Fonctions courtes** : 10-15 lignes max. Si plus long, découper.
- **Getters/setters** : récupérer une donnée = getter, mettre à jour = setter.
- **Classes** : chaque module métier est une classe (OcrService, DocumentClassifier, FieldExtractor, DocumentValidator, DocumentVerifier, ScenarioGenerator, etc.)
- **Factories** : les générateurs de données sont des Factory classes (CompanyFactory, InvoiceFactory, etc.)

### Enums & constantes
- Types de documents : `DocType(StrEnum)` dans `backend/consts/doc_types.py`
- Noms de champs : `FieldName(StrEnum)` dans `backend/consts/fields.py`
- Regex : constantes nommées `EXTRACT_*`, `VALIDATE_*`, `CLASSIFY_*` dans `backend/consts/patterns.py`
- Niveaux de bruit : `NoiseLevel(StrEnum)` dans `dataset/factories/noise.py`
- **Jamais de string literals en dur** pour les invariants métier. Toujours utiliser l'enum correspondante.

### Dataclasses
- `CompanyIdentity` : identité d'entreprise (frozen)
- `DocumentFields` + sous-classes (InvoiceFields, DevisFields, etc.) : modèles de champs par type de document, avec `REQUIRED_FIELDS`, `to_dict()`, `missing_fields()`

### Logging
- Un log structuré à chaque étape du pipeline : `[OCR]`, `[CLASSIFY]`, `[EXTRACT]`, `[VALIDATE]`, `[VERIFY]`
- Format : `%(asctime)s %(levelname)-5s %(name)s — %(message)s`

### Tests
- Tout dans Docker : `make test`, `make lint`
- Un fichier de test par module (test_api, test_classifier, test_extractor, test_validator, test_verifier, test_models, test_company, test_documents, test_generate, test_noise)
- Tests obligatoires pour chaque nouvelle fonctionnalité

### Git workflow
- Branches : `feat/*`, `refactor/*`, `fix/*` → PR → `develop` → PR → `main`
- `develop` et `main` protégées (PR obligatoires)
- CI : lint (ruff) → test (pytest), les deux via Docker

## 10. Ce qui reste à faire

1. **MongoDB — Data Lake 3 zones** (Raw / Clean / Curated)
2. **Frontend métier** (CRM + Conformité, vues Streamlit)
3. **Airflow** — orchestration du pipeline
4. **Déploiement** (Coolify / VPS)

