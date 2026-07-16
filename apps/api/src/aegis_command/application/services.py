from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Sequence
from uuid import UUID

from aegis_command.analytics.risk import RiskPolicy
from aegis_command.analytics.runtime import DetectionRuntime
from aegis_command.application.ports import (
    AssessmentMetrics,
    AssessmentRepository,
    AuditSigner,
    EnforcementAdapter,
)
from aegis_command.domain.models import (
    AssessmentReview,
    AssessmentReviewCreate,
    EnforcementStatus,
    ReceiptVerification,
    SessionAssessment,
    SessionEvent,
)


def canonical_assessment(assessment: SessionAssessment) -> bytes:
    payload = assessment.model_dump(
        mode="json",
        exclude={
            "audit_signature",
            "signature_algorithm",
            "enforcement_status",
            "enforcement_reference",
            "enforcement_error",
            "enforced_at",
            # Telemetry is persisted for investigation, but receipt compatibility intentionally
            # covers the stable decision schema used before the SOC console was introduced.
            "source_event",
        },
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class AssessmentService:
    def __init__(
        self,
        *,
        runtime: DetectionRuntime,
        policy: RiskPolicy,
        repository: AssessmentRepository,
        signer: AuditSigner,
        enforcement: EnforcementAdapter,
        metrics: AssessmentMetrics | None = None,
    ) -> None:
        self._runtime = runtime
        self._policy = policy
        self._repository = repository
        self._signer = signer
        self._enforcement = enforcement
        self._metrics = metrics

    async def assess(self, event: SessionEvent) -> SessionAssessment:
        assessment, _replayed = await self.assess_with_replay(event)
        return assessment

    async def assess_with_replay(self, event: SessionEvent) -> tuple[SessionAssessment, bool]:
        existing = await self._repository.get_by_event_id(event.event_id)
        if existing is not None:
            if self._metrics is not None:
                self._metrics.record_assessment(existing, idempotent=True)
            if existing.enforcement_status in {
                EnforcementStatus.PENDING,
                EnforcementStatus.FAILED,
            }:
                return await self._enforce(existing), True
            return existing, True
        features, anomaly, baseline_scope = self._runtime.assess_features(event)
        risk, decision, factors = self._policy.evaluate(anomaly, features)
        assessment = SessionAssessment(
            event_id=event.event_id,
            session_id=event.session_id,
            user_id=event.user_id,
            anomaly_score=round(anomaly, 4),
            risk_score=risk,
            decision=decision,
            factors=factors,
            features={key: round(value, 4) for key, value in features.items()},
            model_version=self._runtime.detector.version,
            baseline_scope=baseline_scope,
            source_event=event,
        )
        signature = self._signer.sign(canonical_assessment(assessment))
        if signature is not None:
            assessment = assessment.model_copy(
                update={
                    "audit_signature": base64.b64encode(signature).decode("ascii"),
                    "signature_algorithm": self._signer.algorithm,
                }
            )
        claimed = await self._repository.save(assessment)
        if claimed.assessment_id != assessment.assessment_id:
            if self._metrics is not None:
                self._metrics.record_assessment(claimed, idempotent=True)
            if claimed.enforcement_status in {
                EnforcementStatus.PENDING,
                EnforcementStatus.FAILED,
            }:
                return await self._enforce(claimed), True
            return claimed, True
        return await self._enforce(claimed), False

    async def _enforce(self, assessment: SessionAssessment) -> SessionAssessment:
        enforcement = await self._enforcement.enforce(assessment)
        assessment = assessment.model_copy(
            update={
                "enforcement_status": enforcement.status,
                "enforcement_reference": enforcement.reference,
                "enforcement_error": enforcement.error,
                "enforced_at": enforcement.completed_at,
            }
        )
        assessment = await self._repository.save(assessment)
        if self._metrics is not None:
            self._metrics.record_enforcement(enforcement, self._enforcement.name)
            self._metrics.record_assessment(assessment, idempotent=False)
        return assessment

    async def list_recent(self, limit: int) -> Sequence[SessionAssessment]:
        return await self._repository.list_recent(limit)

    async def get(self, assessment_id: UUID) -> SessionAssessment | None:
        return await self._repository.get(assessment_id)

    async def verify_receipt(self, assessment_id: UUID) -> ReceiptVerification | None:
        assessment = await self.get(assessment_id)
        if assessment is None:
            return None
        payload = canonical_assessment(assessment)
        valid = False
        if assessment.audit_signature and self._signer.available:
            try:
                signature = base64.b64decode(assessment.audit_signature, validate=True)
                valid = self._signer.verify(payload, signature)
            except (binascii.Error, ValueError):
                valid = False
        return ReceiptVerification(
            assessment_id=assessment.assessment_id,
            valid=valid,
            algorithm=assessment.signature_algorithm,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
        )

    async def submit_review(
        self,
        assessment_id: UUID,
        reviewer: str,
        body: AssessmentReviewCreate,
    ) -> AssessmentReview | None:
        if await self.get(assessment_id) is None:
            return None
        return await self._repository.save_review(
            AssessmentReview(
                assessment_id=assessment_id,
                reviewer=reviewer,
                disposition=body.disposition,
                comment=body.comment,
            )
        )

    async def list_reviews(self, assessment_id: UUID) -> Sequence[AssessmentReview]:
        return await self._repository.list_reviews(assessment_id)
