from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AccessDecision(StrEnum):
    ALLOW = "ALLOW"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK = "BLOCK"


class EnforcementStatus(StrEnum):
    PENDING = "PENDING"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ReviewDisposition(StrEnum):
    EXPECTED = "EXPECTED"
    BENIGN = "BENIGN"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"


class ResponseAction(StrEnum):
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"
    BLOCK = "BLOCK"


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SessionStatus(StrEnum):
    MONITORING = "MONITORING"
    FLAGGED = "FLAGGED"
    CHALLENGED = "CHALLENGED"
    CONTAINED = "CONTAINED"


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

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, value: list[str]) -> list[str]:
        normalized = [command.strip() for command in value]
        if any(not command for command in normalized):
            raise ValueError("commands cannot contain blank values")
        if any(len(command) > 512 for command in normalized):
            raise ValueError("each command must be at most 512 characters")
        if sum(len(command) for command in normalized) > 16_384:
            raise ValueError("combined command text must be at most 16384 characters")
        return normalized


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
    enforcement_status: EnforcementStatus = EnforcementStatus.PENDING
    enforcement_reference: str | None = None
    enforcement_error: str | None = None
    enforced_at: datetime | None = None
    source_event: SessionEvent | None = None


class AssessmentSummary(BaseModel):
    assessment_id: UUID
    session_id: str
    user_id: str
    assessed_at: datetime
    risk_score: float
    decision: AccessDecision
    enforcement_status: EnforcementStatus = EnforcementStatus.NOT_CONFIGURED


class EnforcementResult(BaseModel):
    status: EnforcementStatus
    reference: str | None = None
    error: str | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReceiptVerification(BaseModel):
    assessment_id: UUID
    valid: bool
    algorithm: str | None
    payload_sha256: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssessmentReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    disposition: ReviewDisposition
    comment: str = Field(min_length=3, max_length=2_000)


class AssessmentReview(BaseModel):
    review_id: UUID = Field(default_factory=uuid4)
    assessment_id: UUID
    reviewer: str = Field(min_length=1, max_length=128)
    disposition: ReviewDisposition
    comment: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: ResponseAction
    note: str = Field(min_length=3, max_length=2_000)


class SessionAction(BaseModel):
    action_id: UUID = Field(default_factory=uuid4)
    assessment_id: UUID
    session_id: str
    action: ResponseAction
    actor: str = Field(min_length=1, max_length=128)
    note: str
    acted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    enforcement_status: EnforcementStatus
    enforcement_reference: str | None = None
    enforcement_error: str | None = None


class SecurityPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_up_threshold: float = Field(ge=1, le=98)
    block_threshold: float = Field(ge=2, le=99)

    @model_validator(mode="after")
    def thresholds_are_ordered(self) -> SecurityPolicyUpdate:
        if self.block_threshold <= self.step_up_threshold:
            raise ValueError("block_threshold must be greater than step_up_threshold")
        return self


class SecurityPolicy(SecurityPolicyUpdate):
    version: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_by: str = Field(default="system", min_length=1, max_length=128)


class SessionListItem(BaseModel):
    assessment_id: UUID
    session_id: str
    user_id: str
    role: str
    started_at: datetime
    assessed_at: datetime
    resource: str
    source_ip: str
    risk_score: float = Field(ge=0, le=100)
    severity: RiskSeverity
    decision: AccessDecision
    status: SessionStatus
    enforcement_status: EnforcementStatus


class SessionPage(BaseModel):
    items: list[SessionListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class RiskTrendPoint(BaseModel):
    timestamp: datetime
    average_risk: float = Field(ge=0, le=100)
    count: int = Field(ge=0)


class OverviewMetrics(BaseModel):
    active_flags: int = Field(ge=0)
    sessions_monitored_24h: int = Field(ge=0)
    average_risk_score: float = Field(ge=0, le=100)
    escalation_count: int = Field(ge=0)
    vault_status: str
    vault_algorithm: str | None


class SocOverview(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: OverviewMetrics
    risk_trend: list[RiskTrendPoint]
    top_sessions: list[SessionListItem]


class SessionTimelineEvent(BaseModel):
    timestamp: datetime
    kind: str
    title: str
    detail: str
    severity: RiskSeverity


class BaselineComparison(BaseModel):
    metric: str
    baseline: float
    actual: float
    unit: str
    deviation_percent: float


class RawLogEntry(BaseModel):
    timestamp: datetime
    event_type: str
    message: str
    metadata: dict[str, str | int | float | bool | None]


class SessionInvestigation(BaseModel):
    assessment_id: UUID
    session_id: str
    user_id: str
    role: str
    started_at: datetime
    ended_at: datetime
    assessed_at: datetime
    resource: str
    source_ip: str
    device_id: str
    risk_score: float = Field(ge=0, le=100)
    severity: RiskSeverity
    decision: AccessDecision
    status: SessionStatus
    enforcement_status: EnforcementStatus
    timeline: list[SessionTimelineEvent]
    baseline: list[BaselineComparison]
    risk_factors: list[RiskFactor]
    raw_logs: list[RawLogEntry]
    reviews: list[AssessmentReview]
    actions: list[SessionAction]


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    session_id: str
    assessment_id: UUID
    event_type: str
    action: str
    actor: str
    risk_score: float = Field(ge=0, le=100)
    detail: str
    status: str


class AuditPage(BaseModel):
    items: list[AuditEntry]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
