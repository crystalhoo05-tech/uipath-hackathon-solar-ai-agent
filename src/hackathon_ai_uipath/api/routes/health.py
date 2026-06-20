"""Health check routes."""

from fastapi import APIRouter, Depends

from hackathon_ai_uipath.api.dependencies import get_app_settings
from hackathon_ai_uipath.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "agent_mode": settings.agent_mode,
        "gemini_model": settings.gemini_model,
    }
