"""Database initialization script."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_database
from app.core.config import settings


async def main():
    """Initialize database with schema."""
    print(f"Initializing database at: {settings.database_path}")

    # Ensure data directory exists
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    # Create tables
    await init_database()

    print("✓ Database initialized successfully")
    print(f"  Location: {settings.database_path}")
    print("\nYou can now:")
    print("  1. Run the API server: uvicorn app.main:app --reload")
    print("  2. Add seed data manually to the database")
    print("  3. Start processing keywords (patterns will be learned automatically)")


if __name__ == "__main__":
    asyncio.run(main())
