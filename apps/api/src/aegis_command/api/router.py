from fastapi import APIRouter

from aegis_command.api.v1.routes import assessments, health, operations, soc, vault

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(assessments.router)
api_router.include_router(vault.router)
api_router.include_router(operations.router)
api_router.include_router(soc.router)
