from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, SecretStr

from finspark.security.pqc import PqcVault

router = APIRouter(prefix="/vault", tags=["pqc-vault"])


class StoreSecretRequest(BaseModel):
    plaintext: Annotated[SecretStr, Field(min_length=1, max_length=16_384)]


class StoreSecretResponse(BaseModel):
    envelope_id: UUID
    algorithm: str
    ciphertext: str


class RetrieveSecretResponse(BaseModel):
    envelope_id: UUID
    plaintext: str


def _vault(request: Request) -> PqcVault:
    vault: PqcVault | None = request.app.state.pqc_vault
    if vault is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PQC runtime is unavailable",
        )
    return vault


@router.get("/status")
async def pqc_status(request: Request) -> dict[str, object]:
    signer = request.app.state.audit_signer
    return {"available": signer.available, "signature_algorithm": signer.algorithm}


@router.post("/secrets", response_model=StoreSecretResponse, status_code=status.HTTP_201_CREATED)
async def store_secret(body: StoreSecretRequest, request: Request) -> dict[str, str]:
    return _vault(request).store(body.plaintext.get_secret_value())


@router.post("/secrets/{envelope_id}/retrieve", response_model=RetrieveSecretResponse)
async def retrieve_secret(
    envelope_id: UUID, request: Request, response: Response
) -> RetrieveSecretResponse:
    plaintext = _vault(request).retrieve(envelope_id)
    if plaintext is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    response.headers["Cache-Control"] = "no-store"
    return RetrieveSecretResponse(envelope_id=envelope_id, plaintext=plaintext)

