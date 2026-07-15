from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finspark.analytics.risk import RiskPolicy
from finspark.analytics.runtime import DetectionRuntime
from finspark.api.router import api_router
from finspark.application.services import AssessmentService
from finspark.core import configure_logging, get_settings
from finspark.infrastructure.database import (
    SqlAssessmentRepository,
    create_engine,
    create_schema,
    session_factory,
)
from finspark.infrastructure.enforcement import LoggingEnforcementAdapter
from finspark.security.pqc import NullAuditSigner, OqsRuntime, PqcUnavailableError, PqcVault

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
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
        signer = oqs_runtime
        vault: PqcVault | None = PqcVault(oqs_runtime)
    except PqcUnavailableError:
        if settings.pqc_required:
            raise
        logger.warning("PQC runtime unavailable; audit signatures and vault are disabled")
        signer = NullAuditSigner()
        vault = None
    repository = SqlAssessmentRepository(session_factory(engine))
    app.state.detection_runtime = runtime
    app.state.audit_signer = signer
    app.state.pqc_vault = vault
    app.state.assessment_service = AssessmentService(
        runtime=runtime,
        policy=RiskPolicy(),
        repository=repository,
        signer=signer,
        enforcement=LoggingEnforcementAdapter(),
    )
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FinSpark Sentinel API",
        version="0.1.0",
        description="Explainable privileged-access risk and post-quantum security API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
    app.include_router(api_router)
    return app


app = create_app()

