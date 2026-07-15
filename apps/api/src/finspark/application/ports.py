from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from finspark.domain.models import SessionAssessment


class AssessmentRepository(Protocol):
    async def save(self, assessment: SessionAssessment) -> None: ...

    async def list_recent(self, limit: int = 50) -> Sequence[SessionAssessment]: ...

    async def get(self, assessment_id: UUID) -> SessionAssessment | None: ...


class AuditSigner(Protocol):
    @property
    def algorithm(self) -> str | None: ...

    @property
    def available(self) -> bool: ...

    def sign(self, payload: bytes) -> bytes | None: ...

    def verify(self, payload: bytes, signature: bytes) -> bool: ...


class EnforcementAdapter(Protocol):
    async def enforce(self, assessment: SessionAssessment) -> None: ...

