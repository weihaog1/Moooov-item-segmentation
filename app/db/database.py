"""Database initialization and schema management."""

import aiosqlite
from pathlib import Path
from app.core.config import settings


async def init_database() -> None:
    """Initialize SQLite database with required tables."""
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Dictionary tables
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_name, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(normalized_name)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS product_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                category TEXT,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_terms ON product_terms(normalized_term)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS color_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_color_terms ON color_terms(normalized_term)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audience_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_audience_terms ON audience_terms(normalized_term)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_scenario_terms ON scenario_terms(normalized_term)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS selling_point_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_selling_point_terms ON selling_point_terms(normalized_term)"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS attribute_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT DEFAULT 'seed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_attribute_terms ON attribute_terms(normalized_term)"
        )

        # Tag mappings for learned patterns
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS tag_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                tag_type TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                source TEXT DEFAULT 'ai_learned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_term, tag_type, language)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tag_mappings ON tag_mappings(normalized_term)"
        )

        # Cache table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword_hash TEXT NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                language TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_hash ON processing_cache(keyword_hash)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_accessed ON processing_cache(last_accessed)"
        )

        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get database connection."""
    return await aiosqlite.connect(settings.database_path)
