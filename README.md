# doc-ingestion-service

FastAPI microservice that accepts business-critical uploads (PDF, DOCX, XLSX), validates them, extracts metadata, versions documents per tenant, and exposes metadata search plus a pre-signed download URL stub for downstream workflows.

## Features

- **Upload** (`POST /api/v1/documents`) — multipart file + `logical_name`; optional `document_id` to append a version
- **Type & size checks** — extension allowlist and configurable max bytes
- **Malware scan stub** — async placeholder hook (`app/services/malware.py`)
- **Metadata extraction** — PDF (pypdf), DOCX (python-docx), XLSX (openpyxl) with SHA-256 and size
- **Versioning** — ordered versions per document aggregate
- **Tenant isolation** — documents scoped by `tenant_id` from identity context
- **RBAC** — viewer / editor / admin roles enforced on protected routes (see `app/core/security.py`)
- **Audit logging** — structured `AUDIT` lines via `app/services/audit.py`
- **Search** (`GET /api/v1/documents/search`) — tenant-scoped metadata search
- **Pre-signed URL stub** (`GET /api/v1/documents/{id}/download-url`)

## Run locally

```bash
cd doc-ingestion-service
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # optional; adjust values
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Identity headers (simulating an API gateway):

| Header | Purpose |
|--------|---------|
| `X-User-Id` | Subject |
| `X-Tenant-Id` | Tenant |
| `X-User-Roles` | Comma-separated roles: `viewer`, `editor`, `admin` |

Optional: `Authorization: Bearer <jwt>` with JSON payload containing `sub`, `tenant_id`, `roles` (demo parsing **without signature verification** — not for production).

## Example upload

```bash
curl -X POST http://localhost:8080/api/v1/documents ^
  -H "X-User-Id: u1" -H "X-Tenant-Id: t1" -H "X-User-Roles: editor" ^
  -F "logical_name=Q1 Report" ^
  -F "file=@./report.pdf"
```

## Tests

```bash
pytest -q
```

## Configuration

See `.env.example`. Runtime settings use `pydantic-settings` (`app/core/config.py`).

## Project layout

```
doc-ingestion-service/
  app/
    main.py
    core/           # settings, RBAC / principal parsing
    api/routes/     # HTTP handlers
    models/         # domain records
    schemas/        # Pydantic IO models
    services/       # audit, malware stub, metadata, storage, versioning, repository
  tests/
```

This codebase is suitable for static analysis, security review drills, and pytest-based CI.

### Review / analysis targets (intentional)

The following patterns exist for training scanners and human reviewers:

| Area | Location |
|------|----------|
| Weak input validation on search `q` | `app/services/search.py`, `GET /api/v1/documents/search` |
| Route without auth | `GET /api/v1/documents/stats/summary` |
| Verbose logging (paths / internal fields) | `upload_document` in `app/api/routes/documents.py` |
| Demo secrets in sample env | `.env.example` |
| Security TODOs | `app/core/security.py`, `app/services/malware.py`, `app/services/repository.py` |
