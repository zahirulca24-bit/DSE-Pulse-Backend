# Cloud Scheduler Setup

Production scheduling must call protected backend routes. The in-process scheduler remains disabled.

## Required values

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-south1"
export SERVICE="dse-pulse-backend"
export COLLECTOR_TOKEN="replace-with-secret-value"
```

Resolve the Cloud Run URL:

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"
```

Create or update the collector job:

```bash
gcloud scheduler jobs create http dse-pulse-daily-collector \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --schedule="0 16 * * 0-4" \
  --time-zone="Asia/Dhaka" \
  --uri="$SERVICE_URL/collector/run" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-Collector-Token=$COLLECTOR_TOKEN" \
  --message-body='{"collect_missing":true}'
```

Use `gcloud scheduler jobs update http` instead when the job already exists.

## Verification

1. Run the Scheduler job manually.
2. Confirm an HTTP success response.
3. Check `/collector/latest` until the job reaches a terminal state.
4. Confirm new OHLC rows exist in Cloud SQL.
5. Confirm no administrative token is exposed in frontend variables or browser requests.

The service remains publicly reachable for read-only frontend routes, while collector and administrative routes remain protected by application tokens.
