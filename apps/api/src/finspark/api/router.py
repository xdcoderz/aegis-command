from fastapi import APIRouter

from finspark.api.v1.routes import assessments, health, vault

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(assessments.router)
api_router.include_router(vault.router)

