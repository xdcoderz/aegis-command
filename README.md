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

## Two-minute judge walkthrough

1. Sign in with the mocked Bank SSO as **SOC analyst**.
2. On **Command center**, select **Run attack simulation**. The live strip follows telemetry through observe, analyze, decide, enforcement, and audit evidence.
3. In the investigation, compare the identity baseline with the session, inspect the factor weights, add an analyst note, and select **Block**.
4. Open **Audit log** to show the risk-engine decision and human response as separate evidence records; export the filtered trail as CSV or printable PDF.
5. Switch the top-bar role to **Security admin**, open **PQC vault**, and run the encrypt/decrypt round trip. The Docker build uses ML-KEM-768 and ML-DSA-65 through Open Quantum Safe. A native-OQS-free local run is clearly labelled compatibility mode and never presented as quantum-safe.
6. In **Policies**, move the step-up or block threshold and save it; later assessments consume the persisted policy version.

The default command-center route polls every eight seconds. Session filters, sorting, pagination, investigation response controls, vault operations, policy changes, and audit exports are wired to real API behavior rather than static UI state.

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
5. Claims the producer event ID so duplicate delivery cannot create duplicate decisions.
6. Signs the canonical decision record when PQC is available.
7. Calls a signed, retry-safe PAM/IAM enforcement webhook and persists its outcome.
8. Persists the explanation, verifiable receipt, and analyst review trail.

See [docs/architecture.md](docs/architecture.md), [docs/threat-model.md](docs/threat-model.md), and [docs/operations.md](docs/operations.md) for system behavior, security assumptions, and deployment controls.

## Security status

This is a production-shaped hackathon implementation with authentication, replay-safe processing, migrations, enforcement integration, health checks, metrics, and automated contract tests. It is not a certified cryptographic module or a replacement for a bank's PAM, SIEM, IAM, HSM, or incident-response controls. Production deployments must move private PQC keys into an HSM/KMS boundary, enforce workload identity, place the API behind a hardened ingress, and complete independent model and security validation.
