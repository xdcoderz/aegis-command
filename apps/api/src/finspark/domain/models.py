from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccessDecision(StrEnum):
    ALLOW = "ALLOW"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK = "BLOCK"


class SessionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=3, max_length=128)
    user_id: str = Field(min_length=2, max_length=128)
    role: str = Field(min_length=2, max_length=128)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_ip: str = Field(min_length=3, max_length=64)
    device_id: str = Field(min_length=2, max_length=128)
    resource: str = Field(min_length=2, max_length=256)
    resource_sensitivity: float = Field(ge=0, le=1)
    commands: list[str] = Field(min_length=1, max_length=200)
    session_duration_minutes: float = Field(gt=0, le=1440)
    privilege_level: int = Field(ge=1, le=5)
    privilege_escalated: bool = False
    failed_auth_attempts: int = Field(default=0, ge=0, le=100)
    bytes_transferred: int = Field(default=0, ge=0)
    approved_for_baseline: bool = False

    @field_validator("occurred_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(UTC)


class RiskFactor(BaseModel):
    key: str
    label: str
    score: float = Field(ge=0, le=100)
    evidence: str


class SessionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    session_id: str
    user_id: str
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    anomaly_score: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=100)
    decision: AccessDecision
    factors: list[RiskFactor]
    features: dict[str, float]
    model_version: str
    baseline_scope: str
    audit_signature: str | None = None
    signature_algorithm: str | None = None


class AssessmentSummary(BaseModel):
    assessment_id: UUID
    session_id: str
    user_id: str
    assessed_at: datetime
    risk_score: float
    decision: AccessDecision

