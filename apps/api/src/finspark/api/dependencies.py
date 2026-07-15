from __future__ import annotations

from fastapi import Request

from finspark.application.services import AssessmentService


def assessment_service(request: Request) -> AssessmentService:
    return request.app.state.assessment_service

