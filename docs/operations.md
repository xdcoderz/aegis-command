# Operations guide

## Authentication and roles

Set `AEGIS_AUTH_ENABLED=true` and provide a JSON mapping in `AEGIS_API_KEYS`:

```text
{"replace-with-observer-key":"observer","replace-with-analyst-key":"analyst","replace-with-admin-key":"admin"}
```

Keys must contain at least 16 characters and are sent as `X-API-Key`. Observers can read decisions,
receipts, reviews, and metrics. Analysts can also submit assessments and dispositions.
Admins additionally control the demonstration PQC vault. The checked-in keys are local demo values;
replace them before any shared deployment.

## Enforcement gateway contract

Configure `AEGIS_ENFORCEMENT_WEBHOOK_URL` and
`AEGIS_ENFORCEMENT_WEBHOOK_SECRET`. The API sends the assessment as canonical JSON with:

- `X-Aegis-Signature: sha256=<HMAC-SHA256 body digest>`
- `X-Idempotency-Key: <event_id>`
- `Content-Type: application/json`

Any 2xx response is successful. Return an `X-Enforcement-Reference` header or a JSON
`{"reference":"..."}` value for incident correlation. Calls have bounded exponential retries and
persist `PENDING`, `SUCCEEDED`, `FAILED`, or `NOT_CONFIGURED` state. Replaying a failed or interrupted
event retries enforcement with the same idempotency key.

New assessments return HTTP 201 and `X-Idempotent-Replay: false`. A duplicate `event_id` returns the
original assessment with HTTP 200 and `X-Idempotent-Replay: true`.

## Health and telemetry

- `/api/v1/health/live` confirms that the process is serving.
- `/api/v1/health/ready` checks database access, the trained detector, PQC, auth, and enforcement.
- `/api/v1/operations/metrics` exposes Prometheus text metrics and requires a valid API key when
  authentication is enabled.
- Supply `X-Correlation-ID` to retain an upstream trace ID; otherwise the API creates one.

## Database lifecycle

The API container runs `alembic upgrade head` before startup. For Kubernetes or multiple replicas,
run the same command once in a release/migration job and start application replicas only after it
succeeds. Keep `AEGIS_AUTO_CREATE_SCHEMA=false` outside local tests.

## Production boundaries

The included vault and ML-DSA keypair are process-local demonstrations. A bank deployment must move
private keys to an HSM/KMS, use OIDC or workload identity instead of static API keys, add ingress rate
limits and mTLS, export audit records to immutable storage, and operate model validation and incident
response processes.
