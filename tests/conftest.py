"""Pytest configuration and fixtures."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create temporary test database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    # Set test database path
    from app.core.config import settings
    original_path = settings.database_path
    settings.database_path = db_path

    # Initialize database
    from app.db.database import init_database
    await init_database()

    yield db_path

    # Cleanup
    settings.database_path = original_path
    if os.path.exists(db_path):
        os.unlink(db_path)
