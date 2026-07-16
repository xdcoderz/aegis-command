from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from aegis_command.analytics.risk import RiskPolicy
from aegis_command.analytics.runtime import DetectionRuntime
from aegis_command.api.middleware import RequestContextMiddleware
from aegis_command.api.router import api_router
from aegis_command.application.ports import AuditSigner, EnforcementAdapter
from aegis_command.application.services import AssessmentService
from aegis_command.application.soc import SocService
from aegis_command.core import configure_logging, get_settings
from aegis_command.infrastructure.database import (
    SqlAssessmentRepository,
    create_engine,
    create_schema,
    session_factory,
)
from aegis_command.infrastructure.enforcement import (
    LoggingEnforcementAdapter,
    SandboxEnforcementAdapter,
    WebhookEnforcementAdapter,
)
from aegis_command.infrastructure.observability import OperationalMetrics
from aegis_command.security.pqc import (
    DevelopmentVault,
    NullAuditSigner,
    OqsRuntime,
    PqcUnavailableError,
    PqcVault,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.auth_enabled and not settings.api_keys:
        raise RuntimeError("Authentication is enabled but AEGIS_API_KEYS is empty")
    if settings.enforcement_webhook_url and settings.enforcement_webhook_secret is None:
        raise RuntimeError(
            "AEGIS_ENFORCEMENT_WEBHOOK_SECRET is required when a webhook is configured"
        )
    engine = create_engine(settings.database_url)
    if settings.auto_create_schema:
        await create_schema(engine)
    runtime = DetectionRuntime.bootstrap(
        seed=settings.model_seed,
        contamination=settings.model_contamination,
    )
    try:
        oqs_runtime = OqsRuntime(
            kem_algorithm=settings.pqc_kem_algorithm,
            signature_algorithm=settings.pqc_signature_algorithm,
        )
        signer: AuditSigner = oqs_runtime
        vault: PqcVault | DevelopmentVault = PqcVault(oqs_runtime)
        vault_algorithm: str | None = vault.algorithm
    except PqcUnavailableError:
        if settings.pqc_required:
            raise
        logger.warning(
            "PQC runtime unavailable; using the clearly labelled local vault compatibility mode"
        )
        signer = NullAuditSigner()
        vault = DevelopmentVault()
        vault_algorithm = vault.algorithm
    repository = SqlAssessmentRepository(session_factory(engine))
    risk_policy = RiskPolicy()
    stored_policy = await repository.get_policy()
    if stored_policy is not None:
        risk_policy.configure(
            step_up_threshold=stored_policy.step_up_threshold,
            block_threshold=stored_policy.block_threshold,
        )
    if settings.enforcement_webhook_url:
        assert settings.enforcement_webhook_secret is not None
        enforcement: EnforcementAdapter = WebhookEnforcementAdapter(
            url=settings.enforcement_webhook_url,
            secret=settings.enforcement_webhook_secret.get_secret_value(),
            timeout_seconds=settings.enforcement_timeout_seconds,
            max_attempts=settings.enforcement_max_attempts,
        )
    elif settings.enforcement_sandbox_enabled:
        enforcement = SandboxEnforcementAdapter()
    else:
        enforcement = LoggingEnforcementAdapter()
    app.state.detection_runtime = runtime
    app.state.audit_signer = signer
    app.state.pqc_vault = vault
    app.state.assessment_repository = repository
    app.state.enforcement_adapter = enforcement
    app.state.assessment_service = AssessmentService(
        runtime=runtime,
        policy=risk_policy,
        repository=repository,
        signer=signer,
        enforcement=enforcement,
        metrics=app.state.metrics,
    )
    app.state.soc_service = SocService(
        repository=repository,
        runtime=runtime,
        policy=risk_policy,
        enforcement=enforcement,
        vault_available=vault.quantum_safe,
        vault_algorithm=vault_algorithm,
    )
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Aegis Command API",
        version="0.1.0",
        description="Explainable privileged-access risk and post-quantum security API",
        lifespan=lifespan,
    )
    app.state.metrics = OperationalMetrics()
    app.add_middleware(
        RequestContextMiddleware,
        max_request_bytes=settings.max_request_bytes,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Demo-Actor",
            "X-Correlation-ID",
        ],
        expose_headers=["X-Correlation-ID", "X-Idempotent-Replay"],
    )
    app.include_router(api_router)
    return app


app = create_app()
