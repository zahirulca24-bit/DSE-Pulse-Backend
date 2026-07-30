# DSE Pulse

**Bangladesh Stock Market Intelligence Platform**

## Project Status

- **Project Name:** DSE Pulse
- **Date:** 31 July 2026
- **Day:** Friday
- **Time:** 2:11 AM BDT
- **Current Phase:** Phase 1 — Repository Foundation
- **Current Progress:** 0%
- **Deployment Target:** Google Cloud
- **Backend Base:** DSE Pulse Backend
- **Frontend Base:** The Trading Desk

## Final Architecture

```text
User
  │
  ▼
DSE Pulse Frontend — Google Cloud Run
  │
  ▼
DSE Pulse Backend — Google Cloud Run
  │
  ├── PostgreSQL — Google Cloud SQL
  ├── Secret Manager
  ├── Cloud Logging
  └── Cloud Scheduler
          ├── Market data collection
          └── Scanner execution
```

## Core Rules

- Real DSE market data only
- No mock market data or fake signals
- Closed-candle-only calculations
- One phase must be completed and verified before the next phase starts
- Administrative write endpoints must be authenticated
- Scanner runs must be protected against duplicate execution
- Production secrets must not be stored in source control

## Development Roadmap

### Phase 1 — Repository Foundation
**Progress target: 0% → 10%**

- Create the final clean repository structure
- Separate `frontend/` and `backend/`
- Remove nested, duplicate and obsolete files
- Standardize local and production environment configuration
- Lock branch, commit and pull-request workflow
- Prepare production-grade project documentation

**Deliverable:** Clean and runnable DSE Pulse repository

### Phase 2 — Backend Security and Stability
**Progress target: 10% → 25%**

- Protect scanner, database and import write endpoints
- Add admin authentication and authorization
- Configure production CORS allowlist
- Add centralized error handling
- Add health and readiness endpoints
- Add duplicate scanner-run lock and idempotency protection
- Fix dependency and test collection failures

**Deliverable:** Secure and stable backend foundation

### Phase 3 — Market Data Pipeline
**Progress target: 25% → 40%**

- Implement reliable DSE OHLCV import
- Reject invalid OHLC records
- Prevent duplicate `(symbol, trade_date)` rows
- Detect missing dates and stale datasets
- Track the latest verified trading date
- Store import logs and audit history
- Migrate persistence to PostgreSQL

**Deliverable:** Verified real-data pipeline

### Phase 4 — Scanner and Signal Engine
**Progress target: 40% → 58%**

- Use closed-candle-only calculations
- Add trend confirmation
- Add liquidity and turnover filters
- Add volume confirmation
- Add ATR-based stop-loss
- Generate entry zone, TP1 and TP2
- Enforce strict risk-reward validation
- Add market-regime and sector-strength filters
- Apply A+ / A / B+ / Reject grading
- Return exact rejection reasons

**Deliverable:** Production-grade DSE signal engine

### Phase 5 — Frontend Integration
**Progress target: 58% → 75%**

- Dashboard
- Scanner
- Signal Board
- Stock Detail
- Chart Lab
- Watchlist
- Portfolio
- Paper Trading
- Journal
- Data Status
- Admin Import

**Deliverable:** Complete DSE Pulse web application connected to real backend data

### Phase 6 — Testing and Verification
**Progress target: 75% → 86%**

- Backend unit tests
- API integration tests
- Authentication tests
- Signal grading tests
- Stale-data tests
- Duplicate-run tests
- Frontend build verification
- Docker build verification
- Scanner output validation

**Deliverable:** Verified release candidate

### Phase 7 — Google Cloud Preparation
**Progress target: 86% → 94%**

- Backend Dockerfile
- Frontend Dockerfile
- Cloud Run `$PORT` support
- Cloud SQL configuration
- Secret Manager mapping
- Cloud Scheduler endpoints
- Database migration command
- Production logging
- Cloud Build or GitHub Actions deployment workflow

**Deliverable:** Google Cloud-ready application

### Phase 8 — Google Cloud Deployment
**Progress target: 94% → 98%**

Deploy:

- `dse-pulse-frontend`
- `dse-pulse-backend`
- Cloud SQL PostgreSQL
- Secret Manager
- Cloud Scheduler
- Cloud Logging

**Deliverable:** Live DSE Pulse deployment

### Phase 9 — Production Audit
**Progress target: 98% → 100%**

- Verify frontend and backend connectivity
- Verify database persistence
- Verify scanner schedule and authentication
- Verify CORS and admin access control
- Verify real-data import and signal generation
- Verify restart recovery
- Review logs and error monitoring
- Check desktop and mobile interfaces

**Deliverable:** Production-approved DSE Pulse v1.0

## Required Work Order

```text
Repository Foundation
        ↓
Backend Security
        ↓
Market Data Pipeline
        ↓
Scanner and Signal Engine
        ↓
Frontend Integration
        ↓
Automated Testing
        ↓
Google Cloud Preparation
        ↓
Deployment
        ↓
Production Audit
```

## Immediate Next Task

Start **Phase 1 — Repository Foundation** using DSE Pulse Backend as the backend base. The Trading Desk frontend will be migrated only after the backend structure and security baseline are verified.
