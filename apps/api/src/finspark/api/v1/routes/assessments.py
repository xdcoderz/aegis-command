from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from finspark.api.dependencies import assessment_service
from finspark.application.services import AssessmentService
from finspark.domain.models import (
    AssessmentReview,
    AssessmentReviewCreate,
    AssessmentSummary,
    ReceiptVerification,
    SessionAssessment,
    SessionEvent,
)
from finspark.security.auth import Principal, require_roles

router = APIRouter(prefix="/assessments", tags=["assessments"])
Service = Annotated[AssessmentService, Depends(assessment_service)]
Reader = Annotated[Principal, Depends(require_roles("observer", "analyst", "admin"))]
Analyst = Annotated[Principal, Depends(require_roles("analyst", "admin"))]


@router.post("", response_model=SessionAssessment, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    event: SessionEvent, response: Response, service: Service, _principal: Analyst
) -> SessionAssessment:
    assessment, replayed = await service.assess_with_replay(event)
    response.status_code = status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
    response.headers["X-Idempotent-Replay"] = str(replayed).lower()
    return assessment


@router.get("", response_model=list[AssessmentSummary])
async def list_assessments(
    service: Service,
    _principal: Reader,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
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
            enforcement_status=item.enforcement_status,
        )
        for item in assessments
    ]


@router.get("/{assessment_id}", response_model=SessionAssessment)
async def get_assessment(
    assessment_id: UUID, service: Service, _principal: Reader
) -> SessionAssessment:
    assessment = await service.get(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment


@router.get("/{assessment_id}/receipt", response_model=ReceiptVerification)
async def verify_receipt(
    assessment_id: UUID, service: Service, _principal: Reader
) -> ReceiptVerification:
    verification = await service.verify_receipt(assessment_id)
    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return verification


@router.post(
    "/{assessment_id}/reviews",
    response_model=AssessmentReview,
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    assessment_id: UUID,
    body: AssessmentReviewCreate,
    service: Service,
    principal: Analyst,
) -> AssessmentReview:
    review = await service.submit_review(assessment_id, principal.subject, body)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return review


@router.get("/{assessment_id}/reviews", response_model=list[AssessmentReview])
async def list_reviews(
    assessment_id: UUID, service: Service, _principal: Reader
) -> list[AssessmentReview]:
    if await service.get(assessment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return list(await service.list_reviews(assessment_id))
