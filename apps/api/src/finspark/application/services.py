from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from uuid import UUID

from finspark.analytics.risk import RiskPolicy
from finspark.analytics.runtime import DetectionRuntime
from finspark.application.ports import AssessmentRepository, AuditSigner, EnforcementAdapter
from finspark.domain.models import SessionAssessment, SessionEvent


def canonical_assessment(assessment: SessionAssessment) -> bytes:
    payload = assessment.model_dump(
        mode="json", exclude={"audit_signature", "signature_algorithm"}
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
    ) -> None:
        self._runtime = runtime
        self._policy = policy
        self._repository = repository
        self._signer = signer
        self._enforcement = enforcement

    async def assess(self, event: SessionEvent) -> SessionAssessment:
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
        )
        signature = self._signer.sign(canonical_assessment(assessment))
        if signature is not None:
            assessment = assessment.model_copy(
                update={
                    "audit_signature": base64.b64encode(signature).decode("ascii"),
                    "signature_algorithm": self._signer.algorithm,
                }
            )
        await self._repository.save(assessment)
        await self._enforcement.enforce(assessment)
        return assessment

    async def list_recent(self, limit: int) -> Sequence[SessionAssessment]:
        return await self._repository.list_recent(limit)

    async def get(self, assessment_id: UUID) -> SessionAssessment | None:
        return await self._repository.get(assessment_id)

