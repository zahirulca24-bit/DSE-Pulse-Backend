# DSE Pulse

**Bangladesh Stock Market Intelligence Platform**

DSE Pulse is a production-oriented backend for verified Dhaka Stock Exchange market data, deterministic scanning, and strict signal qualification. The project is being prepared for Google Cloud deployment with Cloud Run, Cloud SQL PostgreSQL, Secret Manager, Cloud Logging, and Cloud Scheduler.

## Current Status

- **Date:** 08 August 2026
- **Current priority:** DSE Data Foundation stabilization
- **Current phase:** Data collection, historical completeness, validation, and recovery hardening
- **Deployment target:** Google Cloud
- **Production scheduler rule:** no in-process scheduler in production
- **Data policy:** verified DSE data only; no mock, demo, or synthetic market data

> Current release gate: the market-data foundation must be dependable, duplicate-safe, gap-aware, recoverable, and observable before scanner, backtest, or strategy expansion is treated as the primary development priority.

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

## DSE Data Foundation Plan — 08 August 2026

The immediate objective is to make the DSE dataset complete, duplicate-free, gap-aware, recoverable, and easy to monitor. Scanner, AI signal, and backtest expansion remain secondary until the data foundation is verified.

### Phase 1 — Current Data Audit

Verify the existing data path before changing architecture:

- identify every active market-data source
- identify the canonical database table and any local/raw storage
- verify the latest stored market date
- count symbols and total OHLCV rows
- detect duplicate `(symbol, trade_date)` rows
- detect missing trading dates and symbol-level gaps
- verify manual collector execution
- verify Cloud Scheduler collector execution
- verify collector enabled/disabled state behavior

**Output:** a reproducible Data Health Report that establishes the current baseline.

### Phase 2 — Collector Hardening

Strengthen the existing collector instead of replacing it without evidence:

- persisted collector `enabled` state must gate collection
- `Run Now` must return a durable success/failure result
- frontend refresh must not erase a failed-run error
- add bounded retry and timeout handling
- isolate symbol/source failures so one failure does not abort the full run where safe
- use duplicate-safe/idempotent upsert behavior
- make same-day reruns safe
- persist collection job status and failure reason

### Phase 3 — Historical Backfill Engine

Add targeted historical recovery instead of repeatedly rebuilding the full dataset:

- detect missing symbol/date ranges
- calculate the latest required market date
- fetch only the missing range where the source permits
- backfill symbol-level gaps independently
- rerun validation after backfill
- record unresolved gaps when the upstream source cannot provide data

Example:

```text
ABBANK
Missing: 2026-07-20 → 2026-07-23
Action: fetch and validate only the missing range
```

### Phase 4 — Validation and Canonical Database

Use a clear ingestion pipeline:

```text
Source → Raw Data → Validation → Canonical DSE OHLCV Table
```

Validation requirements:

- `high >= open`
- `high >= close`
- `low <= open`
- `low <= close`
- OHLC prices must be positive
- invalid or suspicious volume must be flagged or rejected according to an explicit rule
- duplicate rows must be detected deterministically
- unknown/unexpected symbols must be reported
- stale data must be detectable
- canonical uniqueness must be enforced on `(symbol, trade_date)`

Repeated collection of the same market day must not create duplicate canonical rows.

### Phase 5 — Automatic Daily Operation and Data Health

After Phases 1–4 are verified, the normal market-day flow should be:

```text
Collect → Validate → Upsert → Gap Check → Health Update
```

The frontend Data Collector / Data Health area should expose:

- Collector ON/OFF
- Last Successful Run
- Last Failed Run
- Latest Market Date
- Total Symbols
- Total Rows
- Missing Data Count
- Failed Symbols
- Gap Count
- Run Now
- Backfill Missing Data

### Data Foundation Completion Gate

The data foundation is considered ready only when all of the following are verified:

- daily collection is reliable
- manual and scheduled collection both work
- collector OFF state is respected
- reruns are idempotent
- duplicate canonical rows are prevented
- historical gaps are detectable
- supported gaps can be backfilled
- failed jobs preserve actionable error details
- latest market date and dataset health are visible
- no mock or synthetic market data is used

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

| Priority | Scope | Status |
|---|---|---|
| 1 | Current Data Audit | Next |
| 2 | Collector Hardening | Planned |
| 3 | Historical Backfill Engine | Planned |
| 4 | Validation & Canonical Database | Planned |
| 5 | Automatic Daily Operation & Data Health | Planned |
| 6 | Scanner / Signal verification on trusted data | After data foundation |
| 7 | Backtest / strategy expansion | After data foundation |

## Immediate Next Work

1. Execute Phase 1 Current Data Audit against the actual repository and stored dataset.
2. Establish latest market date, symbol count, row count, duplicates, and missing-data gaps.
3. Verify manual collector and Cloud Scheduler execution paths.
4. Verify persisted collector enabled/disabled state is authoritative.
5. Produce the Data Health Report before implementing additional collector changes.

## Production Principles

- branch, commit, pull-request, CI, then merge
- one verified batch at a time
- administrative writes require authentication
- production secrets never enter source control
- Cloud Scheduler triggers production jobs
- Cloud Run instances do not run an internal scheduler
- no deployment claim is made until build, migration, connectivity, and persistence are verified
- no data-completeness claim is made without row, symbol, duplicate, gap, and latest-date verification
