"""Health check and statistics endpoints."""

import aiosqlite
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import settings
from app.services.cache import cache_service
from app.db.manager import dictionary_manager

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Verifies:
    - Database connectivity
    - Gemini API configuration (checks if API key is set)

    Returns overall system health status.
    """
    db_healthy = False
    gemini_healthy = False
    details = {}

    # Check database
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            async with db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
        db_healthy = True
        details["database"] = "Connected"
    except Exception as e:
        details["database"] = f"Error: {str(e)}"

    # Check Gemini API key is configured
    try:
        if settings.gemini_api_key and len(settings.gemini_api_key) > 10:
            gemini_healthy = True
            details["gemini"] = "API key configured"
        else:
            details["gemini"] = "API key not configured"
    except Exception as e:
        details["gemini"] = f"Error: {str(e)}"

    status = "healthy" if (db_healthy and gemini_healthy) else "unhealthy"

    return HealthResponse(
        status=status,
        database=db_healthy,
        gemini_api=gemini_healthy,
        details=details,
    )


@router.get("/stats")
async def get_stats() -> dict:
    """
    Get system statistics.

    Returns:
    - Dictionary counts
    - Cache statistics
    - Learned patterns count
    """
    dict_stats = await dictionary_manager.get_stats()
    cache_stats = await cache_service.get_stats()

    return {
        "dictionaries": dict_stats,
        "cache": cache_stats,
        "settings": {
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "learning_enabled": settings.enable_learning,
            "learning_threshold": settings.learning_confidence_threshold,
        },
    }
