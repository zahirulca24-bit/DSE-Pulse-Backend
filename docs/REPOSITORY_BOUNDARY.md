# DSE Pulse Repository Boundary

## Canonical repositories

DSE Pulse uses separate repositories for deployable services.

- **Backend repository:** `zahirulca24-bit/DSE-Pulse-Backend`
- **Frontend repository:** maintained separately and must not be added under this backend repository as a nested app or copied source tree.

## Backend ownership

This repository owns:

- FastAPI routes, schemas, services, repositories, and database access
- DSE OHLC ingestion, collector orchestration, scanner execution, signals, and data-audit APIs
- backend tests and quality gates
- backend container and Google Cloud Run deployment assets
- Cloud SQL PostgreSQL integration and migrations
- backend runtime configuration examples

This repository does not own:

- React/Vite/Next.js pages or components
- frontend authentication screens or browser session state
- Vercel deployment configuration
- UI assets, frontend package manifests, or frontend build output
- duplicated copies of the frontend repository

## Integration rule

The frontend communicates with the backend only through documented HTTP APIs. Shared behavior must be represented by API contracts, schemas, and versioned documentation rather than copied implementation code.

## Production target

The approved target architecture is:

- Backend: Google Cloud Run
- Frontend: separate frontend deployment
- Database: Cloud SQL for PostgreSQL
- Secrets: Google Secret Manager
- Scheduled jobs: Google Cloud Scheduler invoking protected backend endpoints
- Logs: Google Cloud Logging

Local CSV storage remains a development and controlled fallback path. It is not the production source of truth for horizontally scaled Cloud Run instances.
