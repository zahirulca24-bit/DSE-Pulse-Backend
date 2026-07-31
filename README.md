# DSE Pulse

**Bangladesh Stock Market Intelligence Platform**

DSE Pulse is a production-oriented backend for verified Dhaka Stock Exchange market data, deterministic scanning, and strict signal qualification. The project is being prepared for Google Cloud deployment with Cloud Run, Cloud SQL PostgreSQL, Secret Manager, Cloud Logging, and Cloud Scheduler.

## Current Status

- **Date:** 31 July 2026
- **Current phase:** Phase 4 — Scanner & Signal Engine completed
- **Current progress:** 58%
- **Next phase:** Phase 5 — Frontend Integration
- **Deployment target:** Google Cloud
- **Production scheduler rule:** no in-process scheduler in production
- **Data policy:** verified DSE data only; no mock, demo, or synthetic market data

> Release gate: the legacy `scanner_candidates` database schema migration must be merged and verified before Phase 5 begins.

## Target Architecture

```text
DSE Pulse Frontend — Google Cloud Run
              │
              ▼
DSE Pulse Backend — Google Cloud Run
              │
              ├── Google Cloud SQL — PostgreSQL
              ├── Secret Manager
              ├── Cloud Logging
              └── Cloud Scheduler
                    ├── Market-data collection
                    └── Scanner execution
```

## Implemented Capabilities

### Repository and security foundation

- standardized FastAPI repository structure
- environment-based configuration
- production CORS allowlist
- authenticated administrative write endpoints
- health, readiness, and database status contracts
- rollback-safe database sessions
- production in-process scheduler disabled

### Verified market-data pipeline

- strict CSV validation
- positive OHLC price enforcement
- open and close validation inside daily high-low range
- deterministic duplicate handling for `(symbol, trade_date)`
- atomic local CSV merge and replacement
- database-first source selection only when verified rows exist
- verified local CSV fallback
- fail-closed `none` source when no verified dataset exists
- no demo-data fallback

### Scanner and signal engine

- minimum 60 verified OHLC rows per eligible symbol
- approved Phase-1 universe filtering
- deterministic EMA, SMA, RSI, volume, setup, and trend calculations
- strict qualification hard gates
- setup-aware risk/reward calculation
- zero-eligible scans fail closed and are not persisted
- latest valid scanner result remains available after an unusable scan
- scanner candidate persistence with duplicate-symbol protection

## Signal Grading Rules

| Grade | Score | Public status |
|---|---:|---|
| A+ | 95–100 | Qualified only when every hard gate passes |
| A | 90–94 | Qualified only when every hard gate passes |
| B+ | 85–89 | Watch only |
| Reject | Below 85 | Rejected |

A high score alone is not enough. A+/A candidates must also pass:

- bullish trend confirmation
- valid production setup
- positive latest volume
- volume ratio of at least `1.5`
- risk/reward of at least `1.5`
- entry distance within the configured maximum

## Market-Data Safety Rules

- real and verified DSE data only
- no mock, demo, synthetic, or silently generated market data
- invalid rows are rejected instead of repaired with fabricated values
- duplicate rows are handled deterministically
- empty database tables are not considered usable data sources
- source selection is consistent across status, symbol, and OHLC routes
- failed scanner runs do not replace the latest valid result

## Main API Areas

- health and readiness
- database status and initialization
- market-data source status
- symbols and OHLC retrieval
- CSV import and data audit
- collector status and execution
- scanner status, execution, and latest candidates
- public signal-rule metadata

Interactive API documentation is available at `/docs` when the application is running.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Run quality checks:

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

Environment variable names and production requirements are documented in `.env.example` and the files under `docs/`.

## Development Roadmap

| Phase | Scope | Progress |
|---|---|---:|
| 1 | Repository Foundation | 10% complete |
| 2 | Backend Security & Stability | 25% complete |
| 3 | Market Data Pipeline | 40% complete |
| 4 | Scanner & Signal Engine | 58% complete |
| 5 | Frontend Integration | 58% → 75% |
| 6 | Testing & Verification | 75% → 86% |
| 7 | Google Cloud Preparation | 86% → 94% |
| 8 | Google Cloud Deployment | 94% → 98% |
| 9 | Production Audit | 98% → 100% |

## Immediate Next Work

1. Merge and verify the legacy scanner schema migration.
2. Lock the frontend-facing API contract.
3. Begin Phase 5 frontend integration for Dashboard, Scanner, Signal Board, Stock Detail, Data Status, and Admin Import.
4. Keep frontend data strictly connected to verified backend responses; no mock UI data.

## Production Principles

- branch, commit, pull-request, CI, then merge
- one verified batch at a time
- administrative writes require authentication
- production secrets never enter source control
- Cloud Scheduler triggers production jobs
- Cloud Run instances do not run an internal scheduler
- no deployment claim is made until build, migration, connectivity, and persistence are verified
