"""Dictionary manager for database operations with MySQL."""

from typing import Optional
from app.core.config import settings
from app.models.schemas import TagType
from app.db.database import get_pool


class DictionaryManager:
    """Manages dictionary lookups and learned patterns."""

    async def lookup_brand(self, term: str, language: str) -> Optional[float]:
        """Look up brand term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM brands WHERE normalized_name = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_product(self, term: str, language: str) -> Optional[float]:
        """Look up product term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM product_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_color(self, term: str, language: str) -> Optional[float]:
        """Look up color term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM color_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_audience(self, term: str, language: str) -> Optional[float]:
        """Look up audience term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM audience_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_scenario(self, term: str, language: str) -> Optional[float]:
        """Look up scenario term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM scenario_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_selling_point(self, term: str, language: str) -> Optional[float]:
        """Look up selling point term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM selling_point_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_attribute(self, term: str, language: str) -> Optional[float]:
        """Look up attribute term and return confidence if found."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT confidence FROM attribute_terms WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                row = await cursor.fetchone()
                return row[0] if row else None

    async def lookup_learned_tags(
        self, term: str, language: str
    ) -> list[tuple[str, float]]:
        """Look up learned tag mappings for a term."""
        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT tag_type, confidence FROM tag_mappings WHERE normalized_term = %s AND language = %s",
                    (normalized, language),
                )
                return await cursor.fetchall()

    async def add_learned_pattern(
        self, term: str, tag_type: TagType, language: str, confidence: float
    ) -> None:
        """Add or update a learned pattern."""
        if not settings.enable_learning:
            return

        if confidence < settings.learning_confidence_threshold:
            return

        normalized = term.lower()
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO tag_mappings (normalized_term, tag_type, language, confidence, occurrence_count)
                    VALUES (%s, %s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        occurrence_count = occurrence_count + 1,
                        confidence = GREATEST(confidence, %s),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (normalized, tag_type, language, confidence, confidence),
                )
                await conn.commit()

    async def get_stats(self) -> dict:
        """Get dictionary statistics."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                stats = {}
                for table in [
                    "brands",
                    "product_terms",
                    "color_terms",
                    "audience_terms",
                    "scenario_terms",
                    "selling_point_terms",
                    "attribute_terms",
                ]:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row = await cursor.fetchone()
                    stats[table] = row[0] if row else 0

                # Learned patterns
                await cursor.execute(
                    "SELECT COUNT(*) FROM tag_mappings WHERE occurrence_count >= %s",
                    (settings.learning_min_occurrences,),
                )
                row = await cursor.fetchone()
                stats["learned_patterns"] = row[0] if row else 0

                return stats


# Global instance
dictionary_manager = DictionaryManager()
