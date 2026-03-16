# IdentifAI

Smart platform for automated processing of business administrative documents.

## Purpose

Automate the full document management lifecycle: **upload → classification → OCR extraction → verification → distribution** to business applications.

## Supported documents

| Type | Extracted data |
|------|---------------|
| Supplier invoice | SIRET, VAT, amounts excl./incl. tax, issue date |
| Quote | SIRET, VAT, amounts excl./incl. tax, issue date |
| SIRET certificate | SIRET number, company name |
| URSSAF certificate | SIRET, expiration date |
| Kbis extract | SIRET, company name, date |
| Bank details (RIB) | IBAN, BIC, account holder |

## Architecture

```
Upload (PDF/images)
  │
  ▼
Automatic classification
  │
  ▼
OCR (DocTR)
  │
  ▼
Key data extraction
  │
  ▼
Cross-document verification
  │
  ├──▶ CRM
  └──▶ Compliance tool
```

**Data Lake — 3 zones:**
- **Raw**: original documents (PDF, images)
- **Clean**: OCR text
- **Curated**: structured data (JSON)

## Tech stack

- **Backend**: Python (FastAPI)
- **OCR**: DocTR (pre-trained deep learning models, PyTorch)
- **Frontend**: Streamlit
- **Database**: NoSQL (MongoDB)
- **Orchestration**: Airflow
- **Containerization**: Docker / Docker Compose
- **CI/CD**: GitHub Actions
- **Data**: Faker + ReportLab (synthetic documents with scan noise)

## Quick start

```bash
make install          # Create venv + install deps
make up               # Start backend + frontend (Docker)
make generate-noisy   # Generate dataset with scan noise
```

| Command | Description |
|---------|-------------|
| `make install` | Create venv and install dependencies |
| `make generate` | Generate clean dataset (10 companies) |
| `make generate-noisy` | Generate dataset with scan noise |
| `make up` | Build and start Docker containers |
| `make down` | Stop containers |
| `make logs` | Follow container logs |
| `make clean` | Remove dataset output and Docker images |

**Ports:** Backend API `http://localhost:8000` / Frontend `http://localhost:8501`

## License

Academic project.
