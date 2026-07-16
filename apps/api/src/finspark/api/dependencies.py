from __future__ import annotations

from typing import cast

from fastapi import Request

from finspark.application.services import AssessmentService
from finspark.application.soc import SocService


def assessment_service(request: Request) -> AssessmentService:
    return cast(AssessmentService, request.app.state.assessment_service)


def soc_service(request: Request) -> SocService:
    return cast(SocService, request.app.state.soc_service)
