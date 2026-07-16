from __future__ import annotations

import secrets
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import Depends, Header, HTTPException, Request, status

from finspark.core import get_settings

Role = Literal["observer", "analyst", "admin"]


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: Role


def _resolve_api_key(candidate: str, configured: dict[str, str]) -> Principal | None:
    for api_key, role in configured.items():
        if secrets.compare_digest(candidate, api_key):
            return Principal(subject=f"api-key:{api_key[-6:]}", role=role)  # type: ignore[arg-type]
    return None


async def authenticated_principal(
    request: Request,
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    demo_actor: Annotated[str | None, Header(alias="X-Demo-Actor", max_length=128)] = None,
) -> Principal:
    settings = get_settings()
    if not settings.auth_enabled:
        subject = demo_actor.strip() if demo_actor and demo_actor.strip() else "local-development"
        local_principal = Principal(subject=subject, role="admin")
        request.state.principal = local_principal
        return local_principal
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    principal = _resolve_api_key(api_key, settings.api_keys)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    request.state.principal = principal
    return principal


def require_roles(*roles: Role) -> Callable[..., Coroutine[Any, Any, Principal]]:
    async def dependency(
        principal: Annotated[Principal, Depends(authenticated_principal)],
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{principal.role}' is not authorized for this operation",
            )
        return principal

    return dependency
