# Spécifications – IdentifAI

## 1. Architecture générale

### Entité centrale : Process

Un **Process** représente une démarche métier complète (ex: conformité fournisseur). Il contient les documents traités et les anomalies détectées.

```
POST   /analyze              (multi-fichiers) → Process (persisté en DB)
PUT    /processes/{id}       (multi-fichiers) → Process (re-run pipeline)
GET    /processes/{id}       → Process
GET    /processes            → list[Process] (actifs uniquement)
DELETE /processes/{id}       → Process (soft delete, status=cancelled)

POST   /ocr                  (fichier unique) → résultat OCR (pas de Process)
POST   /verify               (batch pré-traité) → Process (persisté en DB)
```

### Modèle Process (backend)

```
Process
├── id: str
├── type: ProcessType ("conformite_fournisseur")
├── status: ProcessStatus ("pending" | "valid" | "error" | "cancelled")
├── created_at: str
├── deleted_at: str | None           ← soft delete
├── documents: list[ProcessDocument]
│   └── doc_type, filename, fields
└── anomalies: list[ProcessAnomaly]
    └── type (AnomalyType), severity, message, document_refs, field?
```

### ProcessRunner

```
ProcessRunner.run(documents, definition)
  ├── _create_pending() → insert en DB avec status=PENDING
  ├── _execute()
  │   ├── _collect_document_anomalies() → validator → ProcessAnomaly[]
  │   ├── _check_missing_documents() → required vs fournis → ProcessAnomaly[]
  │   ├── _collect_cross_doc_anomalies() → verifier → ProcessAnomaly[]
  │   ├── _compute_status() → ERROR si ≥1 error, sinon VALID
  │   └── update en DB avec résultat final
  └── return Process

ProcessRunner.rerun(process, documents, definition)
  ├── status → PENDING (update DB)
  └── _execute() → même pipeline, même process ID
```

### MongoDB (`backend/db.py`)

```
ProcessRepository
├── insert(process)               → insert_one
├── update(process)               → replace_one
├── soft_delete(id, deleted_at)   → $set status=cancelled, deleted_at
├── find_by_id(id)                → find_one
└── find_active()                 → find({deleted_at: None})
```

Collection `processes`, index sur `status` + `created_at`. Anomalies embedded.

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
| Check | AnomalyType | Sévérité |
|-------|-------------|----------|
| Cohérence SIRET facture ↔ attestations | `siret_mismatch` | error |
| Attestation URSSAF expirée | `expired_attestation` | error |
| Montant paiement ≠ TTC facture | `payment_amount_mismatch` | error |
| TVA ≠ HT × taux | `tva_mismatch` | warning |
| Paiement orphelin (facture inexistante) | `orphan_payment` | warning |
| Facture sans paiement associé | `missing_payment` | warning |
| CA déclaré < 90% du HT facturé | `undeclared_revenue` | warning |

### Anomalies niveau Process (ajoutées par ProcessRunner)
| AnomalyType | Sévérité | Source |
|-------------|----------|--------|
| `missing_field` | warning | validator |
| `invalid_format` | warning | validator |
| `missing_document` | error | ProcessRunner |

## 6. Process Definitions

### `backend/consts/process_definitions.py`

Chaque `ProcessDefinition` déclare les doc types requis pour un process :

```python
CONFORMITE_FOURNISSEUR = ProcessDefinition(
    process_type=ProcessType.CONFORMITE_FOURNISSEUR,
    required_doc_types=frozenset({
        DocType.FACTURE, DocType.ATTESTATION_SIRET, DocType.ATTESTATION_URSSAF,
        DocType.KBIS, DocType.RIB, DocType.PAYMENT, DocType.URSSAF_DECLARATION,
    }),
)
```

## 7. Front-ends métiers (Streamlit)

- **CRM** : afficher fournisseur, SIRET, coordonnées bancaires
- **Conformité** : afficher statut des attestations, alertes d'expiration

## 8. Dataset

### Structure
```
dataset/
├── factories/
│   ├── company.py    → CompanyFactory + CompanyIdentity (dataclass)
│   ├── documents.py  → InvoiceFactory, DevisFactory, AttestationSiretFactory, etc.
│   └── noise.py      → ScanSimulator + NoiseLevel (enum)
├── models.py         → Alteration, ScenarioDefinition, ProcessRecord, DocumentRecord, AnomalyDetail
├── consts.py         → DocType, AnomalyType, Severity, FieldName, ANOMALY_SEVERITY, PROCESS_REQUIRED_DOCS
├── scenarios.py      → SCENARIOS (8 ScenarioDefinition)
├── builder.py        → ScenarioBuilder
├── generate.py       → CLI entry point
├── company.py        → shims rétro-compatibles
├── documents.py      → shims rétro-compatibles
└── noise.py          → shims rétro-compatibles
```

### Modèle de scénario par altérations

Un scénario déclare un `ProcessType` + des altérations (happy path = aucune altération) :

```python
ScenarioDefinition(
    name="mauvais_siret",
    process_type=ProcessType.CONFORMITE_FOURNISSEUR,
    alterations=[Alteration(DocType.INVOICE, AnomalyType.SIRET_MISMATCH)],
    omitted_docs=[],
)
```

Le builder :
1. Lit les `required_doc_types` du `ProcessDefinition` correspondant
2. Retire les `omitted_docs`
3. Génère chaque document (factory.create)
4. Applique les altérations (wrong siret, expired date, wrong amount...)
5. Applique le noise
6. Calcule le status (anomalies → error/valid)
7. Écrit le `ProcessRecord` (metadata.json)

### 8 scénarios métier
| Dossier | Altérations | Status attendu |
|---------|------------|----------------|
| `happy_path/` | aucune | valid |
| `missing_payment/` | MISSING_PAYMENT sur invoice, omit payment | valid (warning) |
| `mauvais_siret/` | SIRET_MISMATCH sur invoice | error |
| `revenus_sous_declares/` | UNDECLARED_REVENUE sur declaration | valid (warning) |
| `incoherence_tva/` | TVA_MISMATCH sur invoice | valid (warning) |
| `attestation_expiree/` | EXPIRED_ATTESTATION sur attestation_urssaf | error |
| `paiement_sans_facture/` | ORPHAN_PAYMENT sur payment, omit invoice | valid (warning) |
| `montant_paiement_incorrect/` | PAYMENT_AMOUNT_MISMATCH sur payment | error |

### Output : ProcessRecord (metadata.json)

```json
{
  "id": "uuid",
  "type": "conformite_fournisseur",
  "scenario_name": "happy_path",
  "status": "valid",
  "noise_level": "none",
  "documents": [...],
  "anomalies_expected": [...],
  "created_at": "..."
}
```

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

## 9. Conteneurisation

```yaml
services:
  mongo:     # MongoDB 7 (port 27017), volume mongo_data
  backend:   # FastAPI (port 8000), healthcheck /health, depends_on mongo
  frontend:  # Streamlit (port 8501), depends_on backend
  test:      # pytest (profile: test), depends_on mongo
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

## 10. Conventions de code

### Principes
- **SRP** : une fonction = une responsabilité. Si une fonction fait plus d'une chose, la découper.
- **Pas d'imbrication** : jamais plus d'un niveau de `if` ou `for`. Extraire dans des méthodes privées.
- **Fonctions courtes** : 10-15 lignes max. Si plus long, découper.
- **Getters/setters** : récupérer une donnée = getter, mettre à jour = setter.
- **Classes** : chaque module métier est une classe (OcrService, DocumentClassifier, FieldExtractor, DocumentValidator, DocumentVerifier, ProcessRunner, ScenarioBuilder, etc.)
- **Factories** : les générateurs de données sont des Factory classes (CompanyFactory, InvoiceFactory, etc.)

### Enums & constantes
- Types de documents : `DocType(StrEnum)` dans `backend/consts/doc_types.py`
- Noms de champs : `FieldName(StrEnum)` dans `backend/consts/fields.py`
- Regex : constantes nommées `EXTRACT_*`, `VALIDATE_*`, `CLASSIFY_*` dans `backend/consts/patterns.py`
- Types de process : `ProcessType(StrEnum)` dans `backend/consts/process.py`
- Statuts de process : `ProcessStatus(StrEnum)` dans `backend/consts/process.py` (pending, valid, error, cancelled)
- Types d'anomalies : `AnomalyType(StrEnum)` dans `backend/consts/anomalies.py`
- Sévérité : `Severity(StrEnum)` dans `backend/consts/anomalies.py`
- Niveaux de bruit : `NoiseLevel(StrEnum)` dans `dataset/factories/noise.py`
- **Jamais de string literals en dur** pour les invariants métier. Toujours utiliser l'enum correspondante.

### Dataclasses
- `CompanyIdentity` : identité d'entreprise (frozen)
- `DocumentFields` + sous-classes (InvoiceFields, DevisFields, etc.) : modèles de champs par type de document, avec `REQUIRED_FIELDS`, `to_dict()`, `missing_fields()`
- `Process`, `ProcessDocument`, `ProcessAnomaly` : modèles backend (`backend/process.py`)
- `ProcessDefinition` : définition d'un process (frozen, `backend/consts/process_definitions.py`)
- `ProcessRecord`, `DocumentRecord`, `AnomalyDetail`, `Alteration`, `ScenarioDefinition` : modèles dataset (`dataset/models.py`)

### Logging
- Un log structuré à chaque étape du pipeline : `[OCR]`, `[CLASSIFY]`, `[EXTRACT]`, `[VALIDATE]`, `[VERIFY]`, `[PROCESS]`
- Format : `%(asctime)s %(levelname)-5s %(name)s — %(message)s`

### Tests
- Tout dans Docker : `make test`, `make lint`
- Un fichier de test par module (test_api, test_classifier, test_extractor, test_validator, test_verifier, test_models, test_process, test_process_runner, test_company, test_documents, test_generate, test_scenarios, test_noise)
- Tests obligatoires pour chaque nouvelle fonctionnalité

### Git workflow
- Branches : `feat/*`, `refactor/*`, `fix/*` → PR → `develop` → PR → `main`
- `develop` et `main` protégées (PR obligatoires)
- CI : lint (ruff) → test (pytest), les deux via Docker

## 11. MongoDB

- Service `mongo:7` dans docker-compose, volume persistant `mongo_data`
- Backend connecté via `MONGO_URL` (défaut `mongodb://mongo:27017`)
- Base `identifai` (prod), `identifai_test` (tests)
- Collection unique `processes`, documents embedded
- Index sur `status` + `created_at`
- Soft delete via `deleted_at` (non null = supprimé)

## 12. Ce qui reste à faire

1. **Data Lake 3 zones** (Raw / Clean / Curated) — stockage fichiers (GridFS ou S3)
2. **Frontend métier** (CRM + Conformité, vues Streamlit connectées aux routes CRUD)
3. **Airflow** — orchestration du pipeline
4. **Déploiement** (Coolify / VPS)
