"""Pytest configuration and fixtures for MySQL tests."""

import pytest
import asyncio
import aiomysql
from app.core.config import settings
from app.db import database


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create temporary test database in MySQL."""
    # Use test database name
    test_db_name = f"{settings.db_name}_test"

    # Save original database name
    original_db_name = settings.db_name

    try:
        # Create test database
        conn = await aiomysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
        )
        async with conn.cursor() as cursor:
            await cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
            await cursor.execute(
                f"CREATE DATABASE {test_db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()

        # Update settings to use test database
        settings.db_name = test_db_name

        # Close any existing pool
        await database.close_pool()

        # Initialize test database with schema
        await database.init_database()

        yield test_db_name

    finally:
        # Cleanup: close pool and drop test database
        await database.close_pool()

        conn = await aiomysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
        )
        async with conn.cursor() as cursor:
            await cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
        conn.close()

        # Restore original database name
        settings.db_name = original_db_name
