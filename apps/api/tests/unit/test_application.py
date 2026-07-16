from aegis_command.analytics.risk import RiskPolicy
from aegis_command.analytics.runtime import DetectionRuntime
from aegis_command.analytics.synthetic import SyntheticSessionGenerator
from aegis_command.application.services import AssessmentService
from aegis_command.domain.models import EnforcementResult, EnforcementStatus, SessionAssessment
from aegis_command.infrastructure.database import InMemoryAssessmentRepository
from aegis_command.infrastructure.enforcement import LoggingEnforcementAdapter
from aegis_command.security.pqc import NullAuditSigner


class RecoveringEnforcementAdapter:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "test-gateway"

    async def enforce(self, assessment: SessionAssessment) -> EnforcementResult:
        self.calls += 1
        if self.calls == 1:
            return EnforcementResult(
                status=EnforcementStatus.FAILED,
                error="temporary gateway outage",
            )
        return EnforcementResult(
            status=EnforcementStatus.SUCCEEDED,
            reference=f"gateway:{assessment.event_id}",
        )


async def test_assessment_is_persisted() -> None:
    repository = InMemoryAssessmentRepository()
    service = AssessmentService(
        runtime=DetectionRuntime.bootstrap(seed=2026, contamination=0.08),
        policy=RiskPolicy(),
        repository=repository,
        signer=NullAuditSigner(),
        enforcement=LoggingEnforcementAdapter(),
    )

    assessment = await service.assess(SyntheticSessionGenerator(9).normal(0))
    stored = await service.get(assessment.assessment_id)

    assert stored == assessment
    assert stored.audit_signature is None


async def test_failed_enforcement_is_retried_on_idempotent_replay() -> None:
    repository = InMemoryAssessmentRepository()
    enforcement = RecoveringEnforcementAdapter()
    service = AssessmentService(
        runtime=DetectionRuntime.bootstrap(seed=2026, contamination=0.08),
        policy=RiskPolicy(),
        repository=repository,
        signer=NullAuditSigner(),
        enforcement=enforcement,
    )
    event = SyntheticSessionGenerator(19).normal(0)

    failed = await service.assess(event)
    recovered = await service.assess(event)

    assert failed.enforcement_status == EnforcementStatus.FAILED
    assert recovered.assessment_id == failed.assessment_id
    assert recovered.enforcement_status == EnforcementStatus.SUCCEEDED
    assert recovered.enforcement_reference == f"gateway:{event.event_id}"
    assert enforcement.calls == 2
    assert len(await service.list_recent(10)) == 1
