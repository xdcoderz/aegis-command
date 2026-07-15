# ADR 0001: Start as a modular monolith

- Status: Accepted
- Date: 2026-07-15

## Decision

Implement the API, analytics runtime, policy engine, persistence adapter, and PQC module in one deployable Python service with explicit internal ports.

## Rationale

The MVP needs transactional consistency between an assessment, its enforcement decision, and its signed audit representation. Independent services would add network failure, schema coordination, deployment, and observability work before scale requires it. The chosen boundaries retain a clean extraction path for inference, vault, or ingestion services later.

## Consequences

- One API image and one operational health surface.
- Shared process memory for the initial model and baseline catalog.
- Background training must eventually move out of API startup.
- Interfaces and canonical contracts are mandatory to prevent module coupling.

