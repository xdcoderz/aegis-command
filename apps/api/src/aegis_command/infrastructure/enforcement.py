from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

import httpx

from aegis_command.application.ports import EnforcementAdapter
from aegis_command.domain.models import EnforcementResult, EnforcementStatus, SessionAssessment

logger = logging.getLogger(__name__)


class LoggingEnforcementAdapter(EnforcementAdapter):
    """Replaceable boundary for Keycloak, Teleport, or a bank PAM connector."""

    @property
    def name(self) -> str:
        return "logging"

    async def enforce(self, assessment: SessionAssessment) -> EnforcementResult:
        logger.info(
            "access_decision assessment_id=%s session_id=%s decision=%s risk_score=%.2f",
            assessment.assessment_id,
            assessment.session_id,
            assessment.decision.value,
            assessment.risk_score,
        )
        return EnforcementResult(
            status=EnforcementStatus.NOT_CONFIGURED,
            reference="log-only",
        )


class SandboxEnforcementAdapter(EnforcementAdapter):
    """Deterministic PAM simulator for demonstrations and local product testing."""

    @property
    def name(self) -> str:
        return "sandbox-pam"

    async def enforce(self, assessment: SessionAssessment) -> EnforcementResult:
        action = assessment.decision.value.lower().replace("_", "-")
        logger.info(
            "sandbox_enforcement assessment_id=%s action=%s session_id=%s",
            assessment.assessment_id,
            action,
            assessment.session_id,
        )
        return EnforcementResult(
            status=EnforcementStatus.SUCCEEDED,
            reference=f"sandbox-pam:{action}:{assessment.event_id}",
        )


class WebhookEnforcementAdapter(EnforcementAdapter):
    """Signed, idempotent connector for PAM/IAM enforcement gateways."""

    def __init__(
        self,
        *,
        url: str,
        secret: str,
        timeout_seconds: float,
        max_attempts: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._secret = secret.encode("utf-8")
        self._timeout = timeout_seconds
        self._max_attempts = max_attempts
        self._transport = transport

    @property
    def name(self) -> str:
        return "webhook"

    async def enforce(self, assessment: SessionAssessment) -> EnforcementResult:
        payload = assessment.model_dump(mode="json")
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Aegis-Signature": f"sha256={signature}",
            "X-Idempotency-Key": str(assessment.event_id),
        }
        last_error = "enforcement gateway did not respond"
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = await client.post(self._url, content=body, headers=headers)
                    response.raise_for_status()
                    reference = response.headers.get("X-Enforcement-Reference")
                    if not reference:
                        try:
                            candidate = response.json().get("reference")
                            reference = str(candidate) if candidate else None
                        except (ValueError, AttributeError):
                            reference = None
                    return EnforcementResult(
                        status=EnforcementStatus.SUCCEEDED,
                        reference=reference or f"webhook:{assessment.event_id}",
                    )
                except httpx.HTTPError as error:
                    last_error = f"{type(error).__name__}: {error}"
                    logger.warning(
                        "enforcement_attempt_failed assessment_id=%s attempt=%s/%s error=%s",
                        assessment.assessment_id,
                        attempt,
                        self._max_attempts,
                        last_error,
                    )
                    if attempt < self._max_attempts:
                        await asyncio.sleep(0.15 * (2 ** (attempt - 1)))
        return EnforcementResult(
            status=EnforcementStatus.FAILED,
            error=last_error[:500],
        )
