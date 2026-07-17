# DSE Pulse Backend

FastAPI backend for the separate DSE Pulse frontend. It supports deterministic demo signals, local DSE OHLC CSV ingestion/read APIs, and a manual scanner derived only from the imported local CSV.

## Current scope

- Lightweight health and readiness endpoints
- Deterministic demo fallback signals
- CSV preview and normalized local import
- Local data status, symbol list, and OHLC queries
- Manual deterministic scanner with latest-result persistence
- Central locked grade rules
- Explicit CORS configuration
- Pytest, Ruff, Mypy, GitHub Actions, and Render configuration

This project does **not** include live DSE scraping, broker connectivity, order execution, real trading, Supabase, authentication, paid data vendors, or AI recommendations. The API does not provide financial advice.

## Requirements

- Python 3.11+

## Setup and run

```bash
python -m venv .venv
python -m pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

macOS/Linux:

```bash
source .venv/bin/activate
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI documentation is available at `/docs`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Lightweight process health |
| GET | `/status` | Backend and local CSV status |
| GET | `/scanner/status` | Scanner/data/latest-result readiness |
| POST | `/scanner/run` | Run the local scanner manually |
| GET | `/scanner/latest` | Return the latest stored scan |
| GET | `/scanner/candidates` | Filter latest candidates |
| GET | `/signals` | Latest qualified/watch scan results or demo fallback |
| POST | `/data/ohlc/preview` | Validate CSV without saving |
| POST | `/data/ohlc/import` | Save normalized valid rows locally |
| GET | `/data/status` | Local CSV availability and counts |
| GET | `/symbols` | Alphabetically sorted local symbols |
| GET | `/ohlc/{symbol}` | Local OHLC rows for one symbol |

## Local CSV requirement

The scanner reads only:

```text
storage/dse_ohlc.csv
```

Import a CSV before running the scanner. Accepted required headers are:

```text
symbol,date,open,high,low,close,volume
```

or:

```text
symbol,trade_date,open,high,low,close,volume
```

Optional columns are `trade` and `value`. Imports are normalized to:

```text
symbol,trade_date,open,high,low,close,volume,trade,value
```

A successful CSV replacement clears the previous scanner result so `/signals` cannot use a scan derived from the prior imported dataset.

## Scanner engine

The scanner is manual only. `POST /scanner/run`:

1. Reads the normalized local CSV.
2. Groups rows by uppercase symbol.
3. Sorts each symbol by `trade_date` ascending.
4. Requires at least 60 rows per eligible symbol.
5. Uses the latest imported row as the latest closed row.
6. Calculates indicators with the Python standard library.
7. Applies transparent deterministic scoring.
8. Uses the central grade classifier.
9. Stores at most 50 final candidates in `storage/scanner_latest.json`.

No external site, random value, broker, background worker, or order capability is used.

### Indicators

- SMA 20
- SMA 50
- EMA 20
- EMA 50
- RSI 14 using Wilder smoothing
- 20-row average volume
- Volume ratio
- 20-row high
- 20-row low
- Previous 20-row high for breakout detection

### Setup labels

- `EMA Trend Pullback`
- `20-Day Breakout`
- `RSI Momentum Recovery`
- `SMA Trend Continuation`
- `Rejected / No Setup`

### Scoring model

The total is capped at 100:

| Component | Maximum |
|---|---:|
| Trend alignment | 30 |
| RSI momentum | 20 |
| Volume strength | 20 |
| Deterministic setup | 20 |
| Display-only range ratio | 10 |

The display-only range ratio is:

```text
support = 20-row low
resistance = 20-row high
risk = latest_close - support
reward = resistance - latest_close
ratio = reward / risk
```

Invalid or non-positive ranges produce `0`. This is not a recommendation, position-size calculation, or execution instruction.

### Locked grades

Grade logic exists only in `app/core/signal_rules.py`:

- A+ = 95–100 → `qualified`
- A = 90–94 → `qualified`
- B+ = 85–89 → `watch`
- Reject = below 85 → `rejected`

### Candidate metadata

The OHLC CSV does not contain company or sector columns. `company` therefore remains `null`. A small local map supplies approved sector names for known symbols; unknown symbols return `sector=null` with a warning instead of inventing metadata.

## Scanner endpoints

Run manually:

```bash
curl -X POST http://localhost:8000/scanner/run
```

Read latest result:

```bash
curl http://localhost:8000/scanner/latest
```

Filter latest candidates:

```bash
curl "http://localhost:8000/scanner/candidates?grade=A%2B&signal_status=qualified&limit=20"
```

Supported filters are `grade`, `signal_status`, `sector`, and `limit`. The default limit is 50 and the maximum is 100, although the stored latest candidate set itself is capped at 50.

## `/signals` behavior

- When a valid latest scan exists, `/signals` returns its A+, A, and B+ candidates and labels `data_source` as `local_csv`.
- Reject candidates remain in `/scanner/latest` but are omitted from `/signals`.
- When no valid scanner result exists, `/signals` returns the original deterministic demo fallback and labels `data_source` as `demo`.
- An empty local qualified/watch list remains an empty local result; it does not silently switch to demo data.

## Storage limitations

Default paths:

```text
storage/dse_ohlc.csv
storage/scanner_latest.json
```

These paths are configurable through `OHLC_STORAGE_PATH` and `SCANNER_STORAGE_PATH`.

Local file storage is not durable production storage. Render free-service filesystems may be ephemeral and files can disappear after restart, redeploy, or instance replacement. Supabase/PostgreSQL persistence and a durable scanner-result repository remain future work.

## Safety boundaries

- No live market connection
- No DSE website scraping
- No broker connection
- No order placement
- No real trading
- No background auto-trading worker
- No authentication in this phase
- No AI recommendation
- No financial advice

## Quality checks

```bash
python -m pytest
python -m ruff check .
python -m mypy app
```

## Future integration plan

1. Persistent Supabase/PostgreSQL OHLC storage
2. Persistent scanner result/history repository
3. Controlled data ingestion pipeline
4. Scanner performance optimization for larger datasets
5. Render deployment and runtime verification

Future integrations must preserve the current safety boundaries until separately approved.
