from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from finspark.domain.models import (
    AssessmentReview,
    EnforcementResult,
    SecurityPolicy,
    SessionAction,
    SessionAssessment,
)


class AssessmentRepository(Protocol):
    async def save(self, assessment: SessionAssessment) -> SessionAssessment: ...

    async def list_recent(self, limit: int = 50) -> Sequence[SessionAssessment]: ...

    async def get(self, assessment_id: UUID) -> SessionAssessment | None: ...

    async def get_by_event_id(self, event_id: UUID) -> SessionAssessment | None: ...

    async def save_review(self, review: AssessmentReview) -> AssessmentReview: ...

    async def list_reviews(self, assessment_id: UUID) -> Sequence[AssessmentReview]: ...

    async def save_action(self, action: SessionAction) -> SessionAction: ...

    async def list_actions(
        self, session_id: str | None = None, limit: int = 5_000
    ) -> Sequence[SessionAction]: ...

    async def get_policy(self) -> SecurityPolicy | None: ...

    async def save_policy(self, policy: SecurityPolicy) -> SecurityPolicy: ...


class AuditSigner(Protocol):
    @property
    def algorithm(self) -> str | None: ...

    @property
    def available(self) -> bool: ...

    def sign(self, payload: bytes) -> bytes | None: ...

    def verify(self, payload: bytes, signature: bytes) -> bool: ...


class EnforcementAdapter(Protocol):
    @property
    def name(self) -> str: ...

    async def enforce(self, assessment: SessionAssessment) -> EnforcementResult: ...


class AssessmentMetrics(Protocol):
    def record_assessment(self, assessment: SessionAssessment, *, idempotent: bool) -> None: ...

    def record_enforcement(self, result: EnforcementResult, adapter: str) -> None: ...
