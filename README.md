# FinSpark Sentinel

FinSpark Sentinel is an explainable privileged-access risk engine for the FinSpark Hackathon 2026. It creates and learns behavioral baselines, detects anomalous privileged sessions, produces an interpretable 0–100 risk score, and returns an `ALLOW`, `STEP_UP_AUTH`, or `BLOCK` enforcement decision. Its security module uses ML-KEM envelope encryption for stored secrets and ML-DSA signatures for tamper-evident audit records.

## Architecture

This repository is a production-shaped modular monorepo:

```text
apps/
  api/          FastAPI application, analytics, policies, persistence, PQC
  web/          React + TypeScript analyst console
docs/           Architecture, threat model, and decision records
infra/docker/   Reproducible API and web images
scripts/        Developer and demo workflows
```

The API is intentionally a modular monolith. Domain boundaries and adapter interfaces allow extraction into independent services later, without adding distributed failure modes to the MVP.

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Analyst console: `http://localhost:5173`
- OpenAPI: `http://localhost:8000/docs`
- Readiness: `http://localhost:8000/api/v1/health/ready`

The API image builds Open Quantum Safe `liboqs` and its Python bindings. The readiness endpoint reports whether the PQC runtime and trained model are available.

## Local API development

Python 3.12 or newer is supported. Native PQC is optional for local analytics development but required in the Docker demo and production configuration.

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
set FINSPARK_PQC_REQUIRED=false
fastapi dev src/finspark/main.py
```

Run quality checks:

```bash
pytest
ruff check .
mypy src
```

## Local web development

```bash
cd apps/web
npm ci
npm run dev
```

## Principal API flow

Submit `POST /api/v1/assessments` with a privileged session. The service:

1. Extracts deviation and context features.
2. Scores the session with a fitted Isolation Forest.
3. Combines anomaly, asset sensitivity, privilege, session context, and deterministic rules.
4. Selects an enforcement action from configurable thresholds.
5. Signs the canonical decision record when PQC is available.
6. Persists and returns the complete explanation.

See [docs/architecture.md](docs/architecture.md) and [docs/threat-model.md](docs/threat-model.md) for operational boundaries and security assumptions.

## Security status

This is a hackathon-quality reference implementation, not a certified cryptographic module or a replacement for a bank's PAM, SIEM, IAM, HSM, or incident-response controls. Production deployments must move private PQC keys into an HSM/KMS boundary, enforce workload identity, place the API behind a hardened ingress, and complete independent model and security validation.

