"""Database initialization and schema management for MySQL."""

import aiomysql
from typing import Optional
from app.core.config import settings


# Global connection pool
_pool: Optional[aiomysql.Pool] = None


async def get_pool() -> aiomysql.Pool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            db=settings.db_name,
            autocommit=False,
            minsize=1,
            maxsize=10,
        )
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def init_database() -> None:
    """Initialize MySQL database with required tables."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Dictionary tables
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS brands (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_name VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_brand (normalized_name, language),
                    INDEX idx_brands_name (normalized_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    category VARCHAR(100),
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_product (normalized_term, language),
                    INDEX idx_product_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS color_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_color (normalized_term, language),
                    INDEX idx_color_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audience_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_audience (normalized_term, language),
                    INDEX idx_audience_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS scenario_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_scenario (normalized_term, language),
                    INDEX idx_scenario_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS selling_point_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_selling_point (normalized_term, language),
                    INDEX idx_selling_point_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attribute_terms (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    source VARCHAR(50) DEFAULT 'seed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_attribute (normalized_term, language),
                    INDEX idx_attribute_terms (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            # Tag mappings for learned patterns
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tag_mappings (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    normalized_term VARCHAR(255) NOT NULL,
                    tag_type VARCHAR(50) NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    confidence FLOAT NOT NULL,
                    occurrence_count INT DEFAULT 1,
                    source VARCHAR(50) DEFAULT 'ai_learned',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_tag_mapping (normalized_term, tag_type, language),
                    INDEX idx_tag_mappings (normalized_term)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            # Cache table
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_cache (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    keyword_hash VARCHAR(64) NOT NULL UNIQUE,
                    result_json TEXT NOT NULL,
                    language VARCHAR(10) NOT NULL,
                    hit_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_cache_hash (keyword_hash),
                    INDEX idx_cache_accessed (last_accessed)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

            await conn.commit()


async def get_db() -> aiomysql.Connection:
    """Get database connection from pool."""
    pool = await get_pool()
    return await pool.acquire()
