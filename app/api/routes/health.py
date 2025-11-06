"""Health check and statistics endpoints."""

from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import settings
from app.services.cache import cache_service
from app.db.manager import dictionary_manager
from app.db.database import get_pool

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Verifies:
    - Database connectivity
    - DeepSeek API configuration (checks if API key is set)

    Returns overall system health status.
    """
    db_healthy = False
    deepseek_healthy = False
    details = {}

    # Check database
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchone()
        db_healthy = True
        details["database"] = f"Connected to MySQL at {settings.db_host}:{settings.db_port}"
    except Exception as e:
        details["database"] = f"Error: {str(e)}"

    # Check DeepSeek API key is configured
    try:
        if settings.deepseek_api_key and len(settings.deepseek_api_key) > 10:
            deepseek_healthy = True
            details["deepseek"] = "API key configured"
        else:
            details["deepseek"] = "API key not configured"
    except Exception as e:
        details["deepseek"] = f"Error: {str(e)}"

    status = "healthy" if (db_healthy and deepseek_healthy) else "unhealthy"

    return HealthResponse(
        status=status,
        database=db_healthy,
        deepseek_api=deepseek_healthy,
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
