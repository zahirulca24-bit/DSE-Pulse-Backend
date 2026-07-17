# DSE Pulse Backend

FastAPI backend foundation for the separate DSE Pulse frontend. The service currently supports deterministic demo signals plus local CSV-based DSE OHLC ingestion and read APIs.

## Current scope

- Lightweight health and readiness endpoints
- Deterministic local demo signals
- Central locked signal grading rules
- CSV upload preview without saving
- Normalized local CSV import
- Local data status, symbol list, and OHLC queries
- Explicit CORS origins for local frontend development and one configurable production origin
- Automated tests, linting, type checking, and Render configuration

This phase does **not** include live DSE scraping, broker connectivity, order execution, real trading, Supabase, authentication, paid data vendors, or AI recommendations. The API does not provide financial advice.

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
| GET | `/status` | Backend status plus real local CSV counts when available |
| GET | `/scanner/status` | Scanner readiness without starting a worker |
| GET | `/signals` | Deterministic local demo signals |
| POST | `/data/ohlc/preview` | Validate and preview an uploaded CSV without saving |
| POST | `/data/ohlc/import` | Validate and save normalized valid rows locally |
| GET | `/data/status` | Current local CSV availability and derived counts |
| GET | `/symbols` | Alphabetically sorted symbols from local CSV |
| GET | `/ohlc/{symbol}` | Local OHLC rows for one symbol |

## Supported CSV schema

The upload must contain either:

```text
symbol,date,open,high,low,close,volume
```

or:

```text
symbol,trade_date,open,high,low,close,volume
```

Optional columns:

```text
trade,value
```

Imported files are normalized to:

```text
symbol,trade_date,open,high,low,close,volume,trade,value
```

Validation includes required headers, uppercase symbol normalization, strict `YYYY-MM-DD` dates, numeric OHLC values, integer-compatible volume, non-negative prices, `high >= low`, and numeric optional `trade` and `value` values. Invalid rows are reported and excluded from saved data. Missing data is never invented.

## CSV preview

Upload a multipart file using field name `file`:

```bash
curl -X POST http://localhost:8000/data/ohlc/preview \
  -F "file=@dse_ohlc.csv"
```

The preview endpoint returns counts derived from the uploaded file and at most the first 20 valid normalized rows. It does not write to disk.

## CSV import

```bash
curl -X POST http://localhost:8000/data/ohlc/import \
  -F "file=@dse_ohlc.csv"
```

Only normalized valid rows are saved. An upload containing no valid rows does not overwrite an existing local file.

## Local storage

Default path:

```text
storage/dse_ohlc.csv
```

Configure another path through:

```text
OHLC_STORAGE_PATH
```

The storage directory is created automatically. This is local file storage, not database storage, and it is not production-persistent storage.

**Render warning:** files written to a Render free service filesystem may be ephemeral and can disappear after restart, redeploy, or instance replacement. Supabase or another persistent database integration is still pending.

## OHLC query parameters

`GET /ohlc/{symbol}` supports:

- `limit`: default `100`, maximum `1000`
- `start_date`: optional `YYYY-MM-DD`
- `end_date`: optional `YYYY-MM-DD`

Symbols are matched case-insensitively and returned uppercase. Rows are sorted by `trade_date` descending. Unknown symbols return an empty list; fake OHLC rows are never generated.

## Locked signal rules

The rules exist only in `app/core/signal_rules.py`:

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

`render.yaml` defines a Python 3.11 web service, `/health` health check, production start command, and the default local CSV path. Set `FRONTEND_ORIGIN` in Render before connecting a deployed frontend.

The service can run on Render, but uploaded local CSV files should not be treated as durable storage. Persistent Supabase/database integration remains a future phase.

## Future integration plan

1. Persistent Supabase/PostgreSQL storage
2. Scanner engine integration behind the existing API contract
3. Controlled DSE data ingestion pipeline
4. Render deployment and runtime verification

Future integrations must preserve the current safety boundaries until separately approved.
