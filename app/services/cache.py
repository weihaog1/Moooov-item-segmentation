"""Caching service with two-tier architecture (in-memory + MySQL)."""

import json
import hashlib
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import Optional
from app.core.config import settings
from app.models.schemas import TokenizeResponse
from app.db.database import get_pool


class CacheService:
    """Two-tier cache: in-memory LRU + persistent MySQL."""

    def __init__(self):
        self.memory_cache: OrderedDict = OrderedDict()
        self.max_size = settings.max_cache_size
        self.ttl_seconds = settings.cache_ttl_seconds

    def _make_key(self, keyword: str, language: str) -> str:
        """Generate cache key from keyword and language."""
        normalized = keyword.strip().lower()
        combined = f"{normalized}|{language}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if cache entry is expired."""
        if not self.ttl_seconds:
            return False  # No expiration if TTL is 0

        return datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds)

    async def get(
        self, keyword: str, language: str
    ) -> Optional[TokenizeResponse]:
        """
        Get cached result.

        Args:
            keyword: The keyword
            language: Language code

        Returns:
            Cached TokenizeResponse or None
        """
        cache_key = self._make_key(keyword, language)

        # Try memory cache first
        if cache_key in self.memory_cache:
            result = self.memory_cache[cache_key]
            # Move to end (mark as recently used)
            self.memory_cache.move_to_end(cache_key)
            return result

        # Try MySQL cache
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT result_json, created_at
                    FROM processing_cache
                    WHERE keyword_hash = %s
                    """,
                    (cache_key,),
                )
                row = await cursor.fetchone()

                if row:
                    result_json, created_at = row

                    # Check expiration
                    if self._is_expired(created_at):
                        await self._delete_from_db(cache_key)
                        return None

                    # Update hit count and last accessed
                    await cursor.execute(
                        """
                        UPDATE processing_cache
                        SET hit_count = hit_count + 1,
                            last_accessed = CURRENT_TIMESTAMP
                        WHERE keyword_hash = %s
                        """,
                        (cache_key,),
                    )
                    await conn.commit()

                    # Parse and add to memory cache
                    result = TokenizeResponse.model_validate_json(result_json)
                    self._add_to_memory(cache_key, result)
                    return result

        return None

    async def set(
        self, keyword: str, language: str, result: TokenizeResponse
    ) -> None:
        """
        Store result in cache.

        Args:
            keyword: The keyword
            language: Language code
            result: Processing result
        """
        cache_key = self._make_key(keyword, language)

        # Add to memory cache
        self._add_to_memory(cache_key, result)

        # Add to MySQL cache
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO processing_cache (keyword_hash, result_json, language)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        result_json = VALUES(result_json),
                        last_accessed = CURRENT_TIMESTAMP
                    """,
                    (cache_key, result.model_dump_json(), language),
                )
                await conn.commit()

    def _add_to_memory(self, key: str, value: TokenizeResponse) -> None:
        """Add entry to memory cache with LRU eviction."""
        if key in self.memory_cache:
            self.memory_cache.move_to_end(key)
        else:
            self.memory_cache[key] = value
            # Evict oldest if over capacity
            if len(self.memory_cache) > self.max_size:
                self.memory_cache.popitem(last=False)

    async def _delete_from_db(self, cache_key: str) -> None:
        """Delete expired entry from database."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM processing_cache WHERE keyword_hash = %s",
                    (cache_key,),
                )
                await conn.commit()

    async def clear_expired(self) -> int:
        """Clear all expired cache entries. Returns number of entries cleared."""
        if not self.ttl_seconds:
            return 0

        cutoff = datetime.now() - timedelta(seconds=self.ttl_seconds)
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM processing_cache WHERE created_at < %s",
                    (cutoff,),
                )
                row = await cursor.fetchone()
                count = row[0] if row else 0

                await cursor.execute(
                    "DELETE FROM processing_cache WHERE created_at < %s",
                    (cutoff,),
                )
                await conn.commit()
                return count

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*), SUM(hit_count) FROM processing_cache"
                )
                row = await cursor.fetchone()
                total_entries, total_hits = row if row else (0, 0)

        return {
            "memory_cache_size": len(self.memory_cache),
            "db_cache_entries": total_entries or 0,
            "total_cache_hits": total_hits or 0,
        }


# Global instance
cache_service = CacheService()
