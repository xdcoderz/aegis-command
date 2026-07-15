from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from finspark.api.dependencies import assessment_service
from finspark.application.services import AssessmentService
from finspark.domain.models import AssessmentSummary, SessionAssessment, SessionEvent

router = APIRouter(prefix="/assessments", tags=["assessments"])
Service = Annotated[AssessmentService, Depends(assessment_service)]


@router.post("", response_model=SessionAssessment, status_code=status.HTTP_201_CREATED)
async def create_assessment(event: SessionEvent, service: Service) -> SessionAssessment:
    return await service.assess(event)


@router.get("", response_model=list[AssessmentSummary])
async def list_assessments(
    service: Service, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[AssessmentSummary]:
    assessments = await service.list_recent(limit)
    return [
        AssessmentSummary(
            assessment_id=item.assessment_id,
            session_id=item.session_id,
            user_id=item.user_id,
            assessed_at=item.assessed_at,
            risk_score=item.risk_score,
            decision=item.decision,
        )
        for item in assessments
    ]


@router.get("/{assessment_id}", response_model=SessionAssessment)
async def get_assessment(assessment_id: UUID, service: Service) -> SessionAssessment:
    assessment = await service.get(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment

