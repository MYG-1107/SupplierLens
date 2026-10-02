# SupplierLens

AI-powered supplier verification and procurement risk intelligence platform for businesses.

SupplierLens is a portfolio-grade MVP inspired by the supplier-verification problem surfaced by Razorpay's Fix My Itch initiative. It helps a procurement user submit supplier details and evidence, reconcile identity fields, detect inconsistencies, and generate an explainable verification report.

> **Important:** SupplierLens is a decision-support prototype, not a legal, financial, compliance, or fraud-certification service. Verification coverage depends on the evidence and data sources available to the deployment.

## MVP capabilities

- Supplier verification workspace
- GSTIN format validation
- Cross-field consistency checks
- Document-evidence model with source labels
- Explainable deterministic risk flags
- Optional LLM explanation layer
- Synthetic sample supplier data
- REST API with FastAPI
- Next.js + TypeScript web dashboard
- PostgreSQL-ready persistence layer
- Docker Compose development environment
- GitHub Codespaces configuration
- Automated API tests and CI

## Architecture

```text
Next.js Web App
      |
      v
FastAPI API -----> Verification Engine
      |                  |
      |                  +--> Identity checks
      |                  +--> Consistency checks
      |                  +--> Evidence checks
      |                  +--> Risk signals
      |                  +--> Optional LLM explanation
      v
PostgreSQL (ready)

Future connectors:
GST / Udyam / eCourts / Website intelligence / Document OCR
```

## Repository layout

```text
supplierlens-ai/
├── .devcontainer/
├── .github/workflows/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── utils/
│   │   └── tests/
│   └── web/
├── data/synthetic/
├── docs/
├── docker-compose.yml
└── README.md
```

## Quick start in GitHub Codespaces

### Option A: Docker Compose

```bash
git clone <your-repository-url>
cd SupplierLens
docker compose up --build
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Option B: Run services locally

API:

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS/Codespaces: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Web:

```bash
cd apps/web
npm install
npm run dev
```

## Example API request

```bash
curl -X POST http://localhost:8000/api/v1/verification/check \\
  -H "Content-Type: application/json" \\
  -d @../../data/synthetic/example_supplier.json
```

## Roadmap

### Phase 1 — MVP

Supplier intake, evidence submission, consistency checks, explainable report.

### Phase 2 — AI

OCR, entity resolution using embeddings, anomaly detection, RAG, LLM explanations.

### Phase 3 — Connectors

Permitted official/public data connectors and user-provided verification evidence.

### Phase 4 — Procurement workflow

Approval workflows, audit log, monitoring, verification expiry, alerts, role-based access.

## Security and privacy principles

- Never commit secrets to the repository.
- Treat uploaded supplier documents as sensitive business data.
- Keep an audit trail for evidence and generated findings.
- Separate source evidence from model-generated explanations.
- Make model confidence and verification coverage visible.
- Require human review for high-impact procurement decisions.

## License

MIT
