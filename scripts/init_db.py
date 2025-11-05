"""Initialize MySQL database for item segmentation."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_database, get_pool, close_pool
from app.core.config import settings


async def main():
    """Initialize the MySQL database."""
    print(f"Initializing MySQL database...")
    print(f"  Host: {settings.db_host}:{settings.db_port}")
    print(f"  Database: {settings.db_name}")
    print(f"  User: {settings.db_user}")
    print()

    try:
        # Initialize database schema
        await init_database()
        print("✓ Database tables created successfully")
        print()
        print("Database ready!")
        print()
        print("Next steps:")
        print("  1. Run the API server: uvicorn app.main:app --reload")
        print("  2. Or with Docker: docker-compose up -d")
        print("  3. Add seed data manually to the database if needed")
        print("  4. Start processing keywords (patterns will be learned automatically)")

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
