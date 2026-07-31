# Google Cloud Deployment Preparation

## Target architecture

- Cloud Run: FastAPI backend container
- Artifact Registry: container images
- Cloud SQL for PostgreSQL: production database
- Secret Manager: database URL and administrative tokens
- Cloud Scheduler: protected collector/scanner triggers
- Cloud Logging: application and request logs
- Vercel: frontend, configured with the final Cloud Run service URL

## Container contract

- Application import: `app.main:app`
- Listen address: `0.0.0.0`
- Port: runtime `PORT`, default `8080`
- Production mode: `APP_MODE=production`
- In-process scheduler: `SCANNER_SCHEDULER_ENABLED=false`
- Runtime user: non-root `app`

Cloud Run may start multiple instances. Scheduled scanner or collector execution must be invoked by Google Cloud Scheduler through protected API routes, not by an in-process scheduler.

## Required runtime configuration

Non-secret environment variables:

- `APP_MODE=production`
- `FRONTEND_ORIGIN=<final Vercel production origin>`
- `SCANNER_SCHEDULER_ENABLED=false`
- `OHLC_STORAGE_PATH=/tmp/dse_ohlc.csv`
- `SCANNER_STORAGE_PATH=/tmp/scanner_latest.json`
- `SCANNER_SCHEDULER_STATE_PATH=/tmp/scanner_scheduler_state.json`
- `COLLECTOR_STORAGE_PATH=/tmp/collector_jobs.json`

Secrets supplied from Secret Manager:

- `DATABASE_URL`
- `BACKEND_ADMIN_TOKEN`
- `COLLECTOR_ADMIN_TOKEN`

Local files under `/tmp` are ephemeral and must not be treated as the production source of truth. Cloud SQL is the production persistence layer.

## Public and protected routes

The Cloud Run service is publicly reachable so the Vercel frontend can call read-only endpoints. Administrative, import, collector, and scanner-trigger routes remain protected by application tokens. Never expose administrative tokens to the frontend.

## Build and deployment

`cloudbuild.yaml` builds the image, pushes it to Artifact Registry, and deploys the Cloud Run service. Before running it:

1. Create the Artifact Registry repository named `dse-pulse` in `asia-south1` or override `_REPOSITORY` and `_REGION`.
2. Create the Cloud SQL PostgreSQL instance and database.
3. Create Secret Manager secrets.
4. Grant the Cloud Run runtime service account Secret Manager access and Cloud SQL Client permission.
5. Grant the Cloud Build service account Artifact Registry and Cloud Run deployment permissions.
6. Attach the Cloud SQL instance and secret mappings during the deployment-hardening batch.

## Verification gate

A deployment is not production-ready until all of the following pass:

- backend CI
- Docker image build
- container startup on port `8080`
- `/health` response
- Cloud SQL connection and row-backed readiness
- production CORS with the final Vercel origin
- protected write-route authentication
- Cloud Scheduler authenticated trigger test
- frontend production build using the Cloud Run URL
