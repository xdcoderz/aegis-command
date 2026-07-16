# Aegis Command API

FastAPI service for explainable privileged-access assessment, enforcement coordination, evidence storage, and post-quantum demonstrations.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:AEGIS_PQC_REQUIRED = "false"
fastapi dev src/aegis_command/main.py
```

The local default uses `aegis-command.db` and creates its schema automatically. Docker and hosted deployments use Alembic migrations with PostgreSQL.

## Package boundaries

- `domain` — validated session, decision, enforcement, and audit models
- `application` — assessment and SOC use cases plus integration ports
- `analytics` — baseline construction, features, Isolation Forest, and risk policy
- `security` — authentication, ML-KEM vault envelope, and ML-DSA receipts
- `infrastructure` — SQLAlchemy, enforcement adapters, and metrics
- `api` — versioned HTTP routes, dependencies, and middleware

## Operational controls

The service includes API-key RBAC, database-backed event idempotency, signed retry-safe enforcement webhooks, analyst dispositions, verifiable receipts, readiness checks, correlation IDs, security headers, request-size limits, trusted-host validation, and Prometheus metrics.

See the repository [README](../../README.md), [operations guide](../../docs/operations.md), and [threat model](../../docs/threat-model.md) for configuration and security boundaries.
