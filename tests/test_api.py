"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns API info."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "supported_languages" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "gemini_api" in data


@pytest.mark.asyncio
async def test_tokenize_endpoint_validation():
    """Test tokenize endpoint validates input."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Empty keyword should fail
        response = await client.post(
            "/api/v1/tokenize",
            json={"keyword": ""},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_batch_tokenize_endpoint_validation():
    """Test batch endpoint validates input."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Empty list should fail
        response = await client.post(
            "/api/v1/tokenize/batch",
            json={"keywords": []},
        )
        assert response.status_code == 422

        # Too many keywords should fail
        response = await client.post(
            "/api/v1/tokenize/batch",
            json={"keywords": ["test"] * 101},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_stats_endpoint():
    """Test stats endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "dictionaries" in data
        assert "cache" in data
        assert "settings" in data
