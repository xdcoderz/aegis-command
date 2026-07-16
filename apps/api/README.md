# FinSpark Sentinel API

The service package follows domain/application/infrastructure separation. Run `fastapi dev src/finspark/main.py` from this directory after installing the package in editable mode.

Operational controls include API-key RBAC, database-backed event idempotency, retry-safe signed
enforcement webhooks, analyst dispositions, verifiable PQC receipts, readiness checks, request
correlation, security headers, and Prometheus metrics. See `../../docs/operations.md` for configuration
and deployment guidance.

The SOC console uses these persisted APIs under `/api/v1`:

- `GET /overview` for command-center metrics, trend data, and top risky sessions.
- `GET /sessions` and `GET /sessions/{session_id}` for sortable triage and investigation evidence.
- `POST /sessions/{session_id}/action` for analyst allow, step-up, or block responses.
- `GET|PUT /policies` for versioned thresholds used by subsequent risk decisions.
- `GET /audit` for paginated risk-engine and analyst response records.

OpenAPI request and response schemas remain available at `/docs` during local development.
