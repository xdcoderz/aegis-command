from __future__ import annotations

import logging

from finspark.application.ports import EnforcementAdapter
from finspark.domain.models import SessionAssessment

logger = logging.getLogger(__name__)


class LoggingEnforcementAdapter(EnforcementAdapter):
    """Replaceable boundary for Keycloak, Teleport, or a bank PAM connector."""

    async def enforce(self, assessment: SessionAssessment) -> None:
        logger.info(
            "access_decision assessment_id=%s session_id=%s decision=%s risk_score=%.2f",
            assessment.assessment_id,
            assessment.session_id,
            assessment.decision.value,
            assessment.risk_score,
        )

