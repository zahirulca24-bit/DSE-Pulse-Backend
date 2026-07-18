# DSE Pulse Backend

FastAPI backend for DSE Pulse.

## Current Production Direction — 18 Jul 2026

The approved production storage architecture is **Google Drive**, restricted to one dedicated DSE folder. Supabase is not part of the approved production path.

```text
Single User
  -> DSE Pulse Frontend (Vercel)
  -> FastAPI Backend
  -> Google Drive: one dedicated DSE folder only
  -> DSE_OHLC_MASTER.csv
  -> Local backend cache for fast reads
  -> Scanner / future backtest engine
```

The backend must never require broad access to the user's entire Google Drive.

## Current Status

### Completed

- [x] FastAPI backend foundation
- [x] CSV OHLC validation/preview flow
- [x] Local normalized OHLC storage/cache support
- [x] Google Drive storage adapter implemented
- [x] Fixed Google Drive folder configuration supported
- [x] Fixed master filename configuration supported
- [x] Drive import/upsert flow implemented
- [x] Upsert key locked to `(symbol, trade_date)`
- [x] Refresh Drive master before merge to reduce stale-cache overwrite risk
- [x] Local cache refresh after successful Drive save
- [x] Backend tests/type/lint checks passed at implementation merge
- [x] Render deployment definition includes Drive folder ID and master filename placeholders

### Not Yet Live-Proven

- [ ] Dedicated DSE Google service account created/configured
- [ ] Target Drive folder shared with service-account email
- [ ] Service-account JSON stored in backend runtime secret
- [ ] Live deployed `/drive/status` confirmed connected
- [ ] `DSE_OHLC_MASTER.csv` physically confirmed in target Drive folder
- [ ] App -> Backend -> Drive save proven end-to-end
- [ ] Backend restart/redeploy persistence proof completed
- [ ] Scanner proven against the real Drive-backed dataset

## Security Boundary

The intended permission model is:

```text
Google Drive
├── Personal files                     NO ACCESS
├── Office files                       NO ACCESS
├── Finance files                      NO ACCESS
└── DSE Pulse
    └── Market Data & Backtest Storage EDITOR ACCESS ONLY
```

A dedicated service account is an application identity, not a second human user.

Security rules:

- Use a dedicated DSE service account.
- Share only the approved DSE storage folder with that service-account email.
- Do not use domain-wide delegation.
- Do not grant broad Drive access.
- Do not commit JSON keys or base64 credentials to GitHub.
- Do not return credentials in API responses or logs.

## Environment Configuration

Production-relevant variables:

```env
APP_NAME="DSE Pulse Backend"
APP_VERSION="0.1.0"
APP_MODE="production"
FRONTEND_ORIGIN="https://dse-plus.vercel.app"

OHLC_STORAGE_PATH="storage/dse_ohlc.csv"
SCANNER_STORAGE_PATH="storage/scanner_latest.json"

GOOGLE_DRIVE_FOLDER_ID="1juyZSKZACHQfb9KE1Qd0lcQFHNLT_K6F"
GOOGLE_DRIVE_MASTER_FILENAME="DSE_OHLC_MASTER.csv"
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64=""
```

`GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64` must be stored only as a deployment secret.

The local CSV path is a cache/fallback working file, **not the approved durable production source of truth** on an ephemeral deployment filesystem.

## Google Drive Storage Contract

Target folder:

```text
DSE Pulse
  -> Market Data & Backtest Storage
```

Master file:

```text
DSE_OHLC_MASTER.csv
```

Required OHLC columns:

```text
symbol,trade_date,open,high,low,close,volume
```

Accepted import logic:

1. Validate CSV headers and rows.
2. Normalize symbols and dates.
3. Refresh/download the current Drive master when available.
4. Merge/upsert by `(symbol, trade_date)`.
5. Reject/skip invalid rows according to validation rules.
6. Save the updated master to the configured Drive folder.
7. Refresh local cache only after successful durable save.
8. Return verification counts/status to the frontend.

## Core API Surface

### Health and status

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Process liveness |
| GET | `/status` | Backend/data status |
| GET | `/scanner/status` | Scanner readiness |
| GET | `/drive/status` | Google Drive storage configuration/connection status |

### OHLC data

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/data/ohlc/preview` | Validate CSV without saving |
| POST | `/data/ohlc/import` | Save normalized rows to local working storage |
| POST | `/data/ohlc/import-drive` | Validate, merge/upsert, and persist master data to Google Drive |
| GET | `/data/status` | Data/cache status |
| GET | `/data/audit` | Data verification/audit summary |
| GET | `/symbols` | Available symbols |
| GET | `/ohlc/{symbol}` | OHLC rows for a symbol |

### Scanner

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/scanner/run` | Run scanner manually |
| GET | `/scanner/latest` | Latest scanner result |
| GET | `/scanner/candidates` | Latest filtered candidates |
| GET | `/signals` | Signal output |

Legacy database/Supabase-oriented code or endpoints may still exist for compatibility/history, but they are **not the approved DSE Pulse production storage path** and must not be used to represent current runtime readiness.

## Verified Dataset Reference

Prepared merged dataset currently verified outside the deployed Drive runtime:

- 85,024 valid rows
- 460 symbols
- Full-universe base coverage: 2025-07-02 through 2026-06-30
- Partial July extension through 2026-07-16
- July extension: 54 valid rows across only 6 symbols
- Duplicate `(symbol, trade_date)` keys: 0

Important data-quality rule:

- Track global maximum date separately from coverage.
- Do not claim all 460 symbols are current through the global maximum date.
- Scanner/backtest must account for stale or partial symbol coverage.

## Pre-Market Checklist — Must Finish Before 19 Jul 2026, 10:00 BDT

### P0 — Google Drive Authentication

- [ ] Create/select Google Cloud project for DSE Pulse
- [ ] Enable Google Drive API
- [ ] Create dedicated DSE service account
- [ ] Avoid unnecessary broad IAM roles
- [ ] Share only `Market Data & Backtest Storage` folder with service-account email as Editor
- [ ] Create service-account JSON key securely
- [ ] Base64-encode/store JSON only in backend secret manager
- [ ] Set `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_B64`
- [x] `GOOGLE_DRIVE_FOLDER_ID` is defined in deployment configuration
- [x] `GOOGLE_DRIVE_MASTER_FILENAME` is defined in deployment configuration
- [ ] Set/verify `FRONTEND_ORIGIN`
- [ ] Redeploy backend
- [ ] Verify `GET /health` = healthy
- [ ] Verify `GET /drive/status` = configured and connected

### P0 — Master Data Persistence

- [ ] Import verified master CSV through production app/API
- [ ] Confirm CSV validation passes
- [ ] Save to Google Drive
- [ ] Confirm `DSE_OHLC_MASTER.csv` physically exists in the approved folder
- [ ] Verify 85,024 rows after expected initial import, unless a newer approved dataset is used
- [ ] Verify 460 symbols unless a newer approved universe is used
- [ ] Verify duplicate key count = 0
- [ ] Verify latest-date + coverage warning
- [ ] Re-import overlapping rows and prove idempotent upsert/no duplicates
- [ ] Restart/redeploy backend and prove the durable Drive master can restore/refresh cache

### P0 — Production Frontend/Backend Wiring

- [ ] Verify Vercel `VITE_DSE_API_BASE_URL`
- [ ] Verify production frontend reaches backend
- [ ] Verify CORS with `https://dse-plus.vercel.app`
- [ ] Verify production Data Import preview
- [ ] Verify production Save to Google Drive
- [ ] Verify frontend shows real row/symbol/latest-date results after save
- [ ] Verify no mock/demo market data fallback appears

### P0 — Scanner Readiness

- [ ] Prove scanner reads the real imported dataset/cache
- [ ] Verify expected symbol universe
- [ ] Verify latest/full-coverage status before scan
- [ ] Run one production scan successfully
- [ ] Confirm no demo signal fallback
- [ ] Confirm grading rules are consistent with locked DSE rules
- [ ] A+ = 95-100
- [ ] A = 90-94
- [ ] B+ = 85-89 and Watch/Near only
- [ ] Reject = below 85
- [ ] BUY requires A+/A plus trend, volume, proximity, valid setup, no major rejection, and R:R >= 1.5
- [ ] Verify partial/stale-data handling before market use

## Go / No-Go Gate

### GO

Only when all of these are live-proven:

1. Google Drive authentication works.
2. The app can save/update `DSE_OHLC_MASTER.csv` in the one approved folder.
3. Data survives backend restart/redeploy through Drive restoration/refresh.
4. Frontend can reach backend in production.
5. Scanner can run on the real dataset with no demo fallback.

### NO-GO

Do not treat DSE Pulse as market-ready when any of these remain true:

- Drive authentication is missing.
- Master CSV is not physically verified in Drive.
- Save/import works only locally.
- Frontend/backend runtime connection is unverified.
- Scanner output is demo/fallback/fabricated.
- Data coverage is stale or partial without explicit handling.

## Local Development

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI docs are available at `/docs`.

## Quality Checks

```bash
python -m ruff check .
python -m mypy app
python -m pytest
```

## Scope Boundary

DSE Pulse Backend does not place broker orders or execute real-money trades. Any future live market collection, automated scheduling, alerts, or execution-related feature must be separately approved and tested before production use.