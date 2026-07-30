# DSE Pulse Repository Foundation

**Date:** 31 July 2026  
**Time:** 2:20 AM BDT  
**Phase:** Phase 1 — Repository Foundation  
**Batch:** 1 of 2

## Current repository role

This repository is the backend service for the final DSE Pulse platform. It remains independently runnable while the frontend is prepared as a separate Cloud Run service.

## Canonical backend layout

```text
app/
├── api/routes/       # FastAPI route adapters
├── core/             # configuration and shared business rules
├── data/             # static verified metadata
├── db/               # SQLAlchemy models and database bootstrap
├── repositories/     # persistence adapters
├── schemas/          # request and response contracts
├── services/         # application and domain services
└── main.py            # application entry point

tests/                 # backend automated tests
storage/               # local development fallback only
```

## Environment rules

- `.env.example` is the canonical list of supported variables.
- `.env` and production secrets must never be committed.
- Google Cloud production secrets will be supplied through Secret Manager.
- Local CSV/JSON storage is a development fallback, not the final production database.
- Optional Vercel Blob and legacy Google Drive adapters must fail closed when unconfigured or unavailable.

## Dependency rules

- Runtime dependencies are recorded in `requirements.txt`.
- Development and test dependencies are recorded in `requirements-dev.txt`.
- Python support is locked to 3.11–3.13 for this phase.
- Runtime dependencies must be pinned or constrained to reproducible ranges.

## Phase 1 batch status

Completed in Batch 1:

- project metadata standardized in `pyproject.toml`
- runtime Vercel SDK dependency pinned
- complete environment contract documented
- optional Vercel Blob import changed to fail closed
- Python source and tests compile successfully

Remaining for Batch 2:

- establish CI dependency installation and test execution
- classify and remove obsolete provider-specific deployment files
- document frontend repository boundary and API contract
- verify clean installation and full test suite

No scanner, signal, data-import, database, or trading rules are changed by this foundation batch.
