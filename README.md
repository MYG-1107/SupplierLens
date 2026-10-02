# SupplierLens v0.2.1

**Evidence-first supplier verification and procurement review workspace.**

SupplierLens is a software product concept for a real B2B problem: businesses need a more repeatable way to collect supplier evidence, compare identities across documents, surface inconsistencies, and preserve a review trail before purchasing.

## What changed in v0.2.1

- Real supplier directory backed by a local database
- Dashboard metrics and review queue
- Create supplier workflow
- Evidence/document upload with size/type validation
- Basic text/CSV/JSON field extraction for uploaded evidence
- Deterministic verification engine
- Explainable review signals with evidence and remediation
- Verification history and audit trail
- Supplier Copilot with deterministic mode and optional LLM mode
- JSON report export
- Codespaces/devcontainer support
- GitHub Actions CI
- Docker Compose development workflow

## Product principle

> **A model should explain evidence, not replace it.**

The v0.2.1 verification engine does not claim to certify suppliers or confirm government records. It only analyzes evidence supplied to the application. Connectors to permitted authoritative/public sources should be added behind explicit provider interfaces.

## Architecture

```text
Next.js web UI
      │
      │ same-origin /api rewrite
      ▼
FastAPI
  ├── supplier service
  ├── document service
  ├── verification engine
  ├── Copilot service
  └── audit events
      │
      ▼
SQLite (v0.2.1 local MVP)
```

The API data layer can later move to PostgreSQL without changing the product workflow.

## Run in GitHub Codespaces

Create a Codespace on `main`, then run:

```bash
docker compose up --build
```

Open the forwarded **3000** port for the web app. FastAPI documentation is available on the forwarded **8000** port at `/docs`.

### Useful URLs

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Test the backend

```bash
cd apps/api
python -m pytest -q
```

## Optional LLM mode

Copy `.env.example` to `.env`, then set:

```text
LLM_ENABLED=true
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5
```

The LLM is used only for explaining the latest deterministic verification report. It does not replace the verification engine.

## Current limitations

- Government/public-source verification is not included in v0.2.1.
- OCR for image/PDF documents is scaffolded as an extension point; text/CSV/JSON extraction is functional.
- No authentication/authorization yet.
- SQLite is intended for local MVP use; use PostgreSQL for multi-user deployment.
- Uploaded documents should not contain production personal/financial data during development.

## Roadmap

1. OCR + structured document extraction
2. Entity resolution with embeddings
3. Supplier anomaly model and evaluation dataset
4. RAG over evidence and policy documents
5. Permitted official/public data connectors
6. Team approvals and role-based access
7. Continuous supplier monitoring
8. Production PostgreSQL + object storage
9. Observability, security hardening and audit controls
