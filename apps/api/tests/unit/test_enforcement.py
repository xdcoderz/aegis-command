from __future__ import annotations

import hashlib
import hmac

import httpx

from finspark.analytics.risk import RiskPolicy
from finspark.analytics.runtime import DetectionRuntime
from finspark.analytics.synthetic import SyntheticSessionGenerator
from finspark.application.services import AssessmentService
from finspark.domain.models import EnforcementStatus
from finspark.infrastructure.database import InMemoryAssessmentRepository
from finspark.infrastructure.enforcement import WebhookEnforcementAdapter
from finspark.security.pqc import NullAuditSigner


async def test_webhook_enforcement_is_signed_and_idempotent() -> None:
    observed: dict[str, str] = {}

    async def gateway(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        observed["signature"] = request.headers["X-FinSpark-Signature"]
        observed["idempotency_key"] = request.headers["X-Idempotency-Key"]
        observed["expected_signature"] = (
            "sha256=" + hmac.new(b"gateway-secret", body, hashlib.sha256).hexdigest()
        )
        return httpx.Response(200, json={"reference": "pam-action-42"})

    enforcement = WebhookEnforcementAdapter(
        url="https://pam.example.test/enforce",
        secret="gateway-secret",
        timeout_seconds=1,
        max_attempts=2,
        transport=httpx.MockTransport(gateway),
    )
    service = AssessmentService(
        runtime=DetectionRuntime.bootstrap(seed=2026, contamination=0.08),
        policy=RiskPolicy(),
        repository=InMemoryAssessmentRepository(),
        signer=NullAuditSigner(),
        enforcement=enforcement,
    )
    event = SyntheticSessionGenerator(29).normal(0)

    assessment = await service.assess(event)

    assert assessment.enforcement_status == EnforcementStatus.SUCCEEDED
    assert assessment.enforcement_reference == "pam-action-42"
    assert observed["signature"] == observed["expected_signature"]
    assert observed["idempotency_key"] == str(event.event_id)
