# DSE Pulse Backend

FastAPI backend foundation for the separate DSE Pulse frontend. This phase provides a stable API contract using deterministic local demo data so the frontend can connect safely before real DSE data infrastructure exists.

## Current scope

- Demo/local-only API foundation
- Lightweight process and integration status endpoints
- Deterministic demo signals
- Central locked grading rules
- Explicit CORS origins for local frontend development and one configurable production origin
- Automated tests, linting, type checking, and Render configuration

This phase does **not** include broker connectivity, order execution, live trading, real-time DSE scraping, paid data vendors, Supabase, authentication, or AI recommendations. Nothing returned by this service is financial advice.

## Requirements

- Python 3.11+

## Local setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

## Run locally

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI documentation is available at `/docs` while the app is running.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Lightweight frontend connection test |
| GET | `/status` | Truthful backend and integration status |
| GET | `/scanner/status` | Scanner readiness without starting a worker |
| GET | `/signals` | Deterministic local demo signals |

## Locked signal rules

The rules exist only in `app/core/signal_rules.py` and are consumed by the signal service:

- A+ = 95-100 → `qualified`
- A = 90-94 → `qualified`
- B+ = 85-89 → `watch`
- Reject = below 85 → `rejected`

There is no order, execution, or background trading capability.

## CORS

Local development origins are explicitly allowed:

- `http://localhost:3000`
- `http://localhost:5173`

Set `FRONTEND_ORIGIN` to the deployed frontend origin. Wildcard CORS is not used.

## Quality checks

```bash
python -m pytest
python -m ruff check .
python -m mypy app
```

## Render deployment foundation

`render.yaml` defines a Python 3.11 web service, `/health` health check, and the production start command. Set `FRONTEND_ORIGIN` in Render before connecting a deployed frontend.

## Future integration plan

1. CSV/DSE OHLC ingestion with validated schemas and truthful dataset metadata
2. Supabase/PostgreSQL data adapter
3. Scanner engine integration behind the existing API contract
4. Render deployment and runtime verification

Future integrations must preserve the current safety boundaries until separately approved.
