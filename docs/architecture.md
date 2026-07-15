# System architecture

## Context

FinSpark Sentinel accepts privileged-session telemetry from a PAM, IAM, SIEM, or replay generator. It evaluates behavior against historical user and role baselines and returns a risk-based access decision. Analysts review the decision and its evidence in the web console.

## Runtime components

```mermaid
flowchart LR
  S["PAM / SIEM / synthetic replay"] --> A["FastAPI ingestion"]
  A --> F["Feature and baseline engine"]
  F --> M["Isolation Forest"]
  M --> R["Explainable risk policy"]
  R --> E["Enforcement adapter"]
  R --> Q["ML-DSA audit signer"]
  Q --> P[(PostgreSQL)]
  P --> W["React analyst console"]
  V["PQC vault"] --> K["ML-KEM + HKDF + AES-256-GCM"]
```

## Module boundaries

- **Domain** owns session, assessment, decision, and risk concepts. It has no framework dependencies beyond validation types.
- **Application** orchestrates analytics, policy, signing, persistence, and enforcement ports.
- **Analytics** owns deterministic feature extraction, baselines, synthetic data, model fitting, and inference.
- **Security** owns cryptographic envelopes and signatures behind interfaces.
- **Infrastructure** owns SQLAlchemy persistence and runtime integration.
- **API** owns HTTP translation, versioning, dependency lookup, and error mapping.

## Scaling path

The synchronous assessment path is stateless after model and baseline loading. API replicas can share PostgreSQL and a versioned model artifact. At higher volume, event aggregation and model inference can move behind a durable queue while preserving the application contracts. Baseline updates must be serialized per user to avoid lost updates and must exclude unreviewed high-risk sessions.

## Data classification

Session telemetry is security-sensitive and may contain personal data. Command text should be tokenized or redacted at ingestion. Credentials never enter assessment logs. Vault plaintext is accepted only over authenticated transport and is never persisted or logged.

