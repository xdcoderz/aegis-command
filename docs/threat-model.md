# Threat model

## Protected assets

- Privileged credentials and session artifacts
- Access-decision integrity
- Behavioral profiles and model artifacts
- Analyst identities and audit evidence

## Principal threats and controls

| Threat | Control in this repository | Production follow-up |
|---|---|---|
| Stolen credential used abnormally | User/role deviation features and risk-based enforcement | Integrate real PAM and step-up authentication |
| Audit record modification | Canonical record signed with ML-DSA | Store keys in HSM and export logs to immutable storage |
| Offline theft of vault ciphertext | ML-KEM-derived envelope key and AES-256-GCM | HSM-backed decapsulation, rotation, access approval |
| Model poisoning | High-risk sessions are not baseline-learning inputs | Analyst approval workflow and signed training manifests |
| Replay or duplicate event | Client event ID and timestamp are part of the assessment contract | Enforce idempotency and ingestion windows in the gateway |
| Command injection through telemetry | Telemetry is treated as data; UI escapes strings | Add schema gateway and content redaction |
| Excessive automated blocking | Explainable score and three-way decision | Human override, fail-safe policy, and rollback runbook |

## Explicit non-goals

- Claiming that liboqs is a validated FIPS 140-3 cryptographic module
- Replacing enterprise key custody with process-memory keys
- Automatically accusing an employee based on an anomaly score
- Training on private banking data without governance approval

