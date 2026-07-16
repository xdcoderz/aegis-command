from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from finspark.security.auth import Principal, require_roles

router = APIRouter(prefix="/operations", tags=["operations"])
Operator = Annotated[Principal, Depends(require_roles("observer", "analyst", "admin"))]


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request, _principal: Operator) -> Response:
    return Response(
        content=request.app.state.metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
