from finspark.analytics.risk import RiskPolicy
from finspark.analytics.runtime import DetectionRuntime
from finspark.analytics.synthetic import SyntheticSessionGenerator
from finspark.application.services import AssessmentService
from finspark.infrastructure.database import InMemoryAssessmentRepository
from finspark.infrastructure.enforcement import LoggingEnforcementAdapter
from finspark.security.pqc import NullAuditSigner


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

