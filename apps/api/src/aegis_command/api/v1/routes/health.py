from __future__ import annotations

from fastapi import APIRouter, Request

from aegis_command.core import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    settings = get_settings()
    runtime = request.app.state.detection_runtime
    signer = request.app.state.audit_signer
    vault = request.app.state.pqc_vault
    repository = request.app.state.assessment_repository
    database_ready = await repository.ping()
    ready_state = runtime.detector.fitted and database_ready and (
        signer.available or not settings.pqc_required
    )
    return {
        "status": "ready" if ready_state else "degraded",
        "database": {"ready": database_ready},
        "model": {
            "fitted": runtime.detector.fitted,
            "version": runtime.detector.version,
        },
        "pqc": {
            "available": signer.available,
            "signature_algorithm": signer.algorithm,
            "vault_mode": vault.mode if vault is not None else "disabled",
            "vault_available": vault is not None,
        },
        "authentication": {
            "enabled": settings.auth_enabled,
            "configured_principals": len(settings.api_keys),
        },
        "enforcement": {"adapter": request.app.state.enforcement_adapter.name},
    }
