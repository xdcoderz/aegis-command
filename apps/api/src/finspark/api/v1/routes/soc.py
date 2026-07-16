from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from finspark.api.dependencies import soc_service
from finspark.application.soc import SocService
from finspark.domain.models import (
    AccessDecision,
    AuditPage,
    SecurityPolicy,
    SecurityPolicyUpdate,
    SessionAction,
    SessionActionCreate,
    SessionInvestigation,
    SessionPage,
    SessionStatus,
    SocOverview,
)
from finspark.security.auth import Principal, require_roles

router = APIRouter(tags=["soc-console"])
Service = Annotated[SocService, Depends(soc_service)]
Reader = Annotated[Principal, Depends(require_roles("observer", "analyst", "admin"))]
Analyst = Annotated[Principal, Depends(require_roles("analyst", "admin"))]
Admin = Annotated[Principal, Depends(require_roles("admin"))]
SortOrder = Literal[
    "risk_desc",
    "risk_asc",
    "recent",
    "oldest",
    "user_asc",
    "user_desc",
    "resource_asc",
    "resource_desc",
    "status_asc",
    "status_desc",
]


def _utc_bound(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{name} must include a timezone",
        )
    return value.astimezone(UTC)


@router.get("/overview", response_model=SocOverview)
async def overview(service: Service, _principal: Reader) -> SocOverview:
    return await service.overview()


@router.get("/sessions", response_model=SessionPage)
async def list_sessions(
    service: Service,
    _principal: Reader,
    user: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    resource: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
    min_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
    max_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
    decision: AccessDecision | None = None,
    status_filter: Annotated[SessionStatus | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: SortOrder = "risk_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> SessionPage:
    date_from = _utc_bound(date_from, "date_from")
    date_to = _utc_bound(date_to, "date_to")
    if min_risk is not None and max_risk is not None and min_risk > max_risk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_risk cannot be greater than max_risk",
        )
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from cannot be later than date_to",
        )
    return await service.list_sessions(
        user=user,
        resource=resource,
        min_risk=min_risk,
        max_risk=max_risk,
        decision=decision,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=SessionInvestigation)
async def get_session(
    session_id: str, service: Service, _principal: Reader
) -> SessionInvestigation:
    detail = await service.investigation(session_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return detail


@router.post(
    "/sessions/{session_id}/action",
    response_model=SessionAction,
    status_code=status.HTTP_201_CREATED,
)
async def respond_to_session(
    session_id: str,
    body: SessionActionCreate,
    service: Service,
    principal: Analyst,
) -> SessionAction:
    action = await service.respond(session_id, principal.subject, body)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return action


@router.get("/policies", response_model=SecurityPolicy)
async def get_policy(service: Service, _principal: Reader) -> SecurityPolicy:
    return await service.get_policy()


@router.put("/policies", response_model=SecurityPolicy)
async def update_policy(
    body: SecurityPolicyUpdate, service: Service, principal: Admin
) -> SecurityPolicy:
    return await service.update_policy(body, principal.subject)


@router.get("/audit", response_model=AuditPage)
async def audit_log(
    service: Service,
    _principal: Reader,
    session_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    action: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditPage:
    date_from = _utc_bound(date_from, "date_from")
    date_to = _utc_bound(date_to, "date_to")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from cannot be later than date_to",
        )
    return await service.audit(
        session_id=session_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
