from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    runtime = request.app.state.detection_runtime
    signer = request.app.state.audit_signer
    return {
        "status": "ready" if runtime.detector.fitted else "degraded",
        "model": {
            "fitted": runtime.detector.fitted,
            "version": runtime.detector.version,
        },
        "pqc": {
            "available": signer.available,
            "signature_algorithm": signer.algorithm,
        },
    }

