# DSE Pulse Backend API Contract

## Contract principles

- JSON response fields are defined by Pydantic response models.
- Existing fields must not be renamed or removed without a documented migration.
- New optional fields are preferred over breaking changes.
- Dates use ISO `YYYY-MM-DD` format.
- Symbols are normalized to uppercase.
- Production browser access is restricted by explicit CORS origins.
- Administrative collector actions require `X-Collector-Token` when the collector is enabled.

## Core routes

### Health and runtime

- `GET /health` — process health/readiness summary
- `GET /status` — application and scanner runtime status
- `GET /db/status` — database configuration and connection status
- `POST /db/init` — initialize supported database tables

### Market data

- `POST /data/ohlc/preview` — validate uploaded CSV without saving
- `POST /data/ohlc/import` — import normalized OHLC into local fallback storage
- `POST /data/ohlc/import-db` — import normalized OHLC into the configured database
- `GET /data/status` — local data availability and counts
- `GET /data/source` — active source preference and fallback order
- `GET /data/audit` — database quality and scanner-readiness metrics
- `GET /data/audit/stale-symbols` — symbols behind the latest dataset date
- `GET /symbols` — available symbols
- `GET /ohlc/{symbol}` — OHLC rows with supported filters

### Scanner and signals

- `POST /scanner/run` — execute the scanner through the canonical scanner service
- `GET /scanner/status` — scanner runtime status
- `GET /scanner/candidates` — latest qualified candidates
- `GET /signals` — latest signal projection

### Collector

- `POST /collector/run` — queue a protected collection job
- `GET /collector/latest` — latest collector job
- `GET /collector/history` — collector history
- `GET /collector/status/{job_id}` — one collector job

## Data-source policy

Production market data should use Cloud SQL PostgreSQL. Local CSV is retained for development, controlled imports, tests, and emergency fallback. Google Drive endpoints are legacy compatibility only and must not become the production source of truth.

## Error behavior

- Validation errors use FastAPI/Pydantic `422` responses.
- Missing or invalid collector authorization uses `403` or disabled-state `503` responses.
- Unavailable optional infrastructure must fail closed and must not silently fabricate market data.
- No endpoint may return mock OHLC, fake symbols, or generated trading signals as real market data.

## Change process

Any route removal, field rename, type change, authentication change, or fallback-order change requires:

1. an implementation PR,
2. updated tests,
3. this contract updated in the same PR,
4. frontend migration notes when applicable,
5. passing backend CI before merge.
