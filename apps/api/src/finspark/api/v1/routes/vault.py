from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, SecretStr

from finspark.security.auth import Principal, require_roles
from finspark.security.pqc import DevelopmentVault, PqcVault

router = APIRouter(prefix="/vault", tags=["pqc-vault"])
Reader = Annotated[Principal, Depends(require_roles("observer", "analyst", "admin"))]
Administrator = Annotated[Principal, Depends(require_roles("admin"))]


class StoreSecretRequest(BaseModel):
    plaintext: Annotated[SecretStr, Field(min_length=1, max_length=16_384)]


class StoreSecretResponse(BaseModel):
    envelope_id: UUID
    algorithm: str
    ciphertext: str


class RetrieveSecretResponse(BaseModel):
    envelope_id: UUID
    plaintext: str


Vault = PqcVault | DevelopmentVault


def _vault(request: Request) -> Vault:
    vault: Vault | None = request.app.state.pqc_vault
    if vault is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PQC runtime is unavailable",
        )
    return vault


@router.get("/status")
async def pqc_status(request: Request, _principal: Reader) -> dict[str, object]:
    signer = request.app.state.audit_signer
    vault = _vault(request)
    return {
        "available": True,
        "quantum_safe": vault.quantum_safe,
        "signature_algorithm": signer.algorithm,
        "kem_algorithm": vault.algorithm,
        "envelope_count": vault.envelope_count,
        "mode": vault.mode,
    }


@router.post("/secrets", response_model=StoreSecretResponse, status_code=status.HTTP_201_CREATED)
async def store_secret(
    body: StoreSecretRequest, request: Request, _principal: Administrator
) -> dict[str, str]:
    return _vault(request).store(body.plaintext.get_secret_value())


@router.post("/secrets/{envelope_id}/retrieve", response_model=RetrieveSecretResponse)
async def retrieve_secret(
    envelope_id: UUID,
    request: Request,
    response: Response,
    _principal: Administrator,
) -> RetrieveSecretResponse:
    plaintext = _vault(request).retrieve(envelope_id)
    if plaintext is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    response.headers["Cache-Control"] = "no-store"
    return RetrieveSecretResponse(envelope_id=envelope_id, plaintext=plaintext)
