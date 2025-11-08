"""Extract multi-word patterns from learned data for spaCy tokenization."""

from typing import List, Dict
from app.db.database import get_pool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extract multi-word patterns from tag_mappings table."""

    async def extract_multiword_patterns(
        self,
        language: str,
        min_occurrences: int = None
    ) -> List[str]:
        """
        Extract multi-word entities from tag_mappings.

        Args:
            language: Language code
            min_occurrences: Minimum occurrence count (defaults to pattern_matching_min_occurrences)

        Returns:
            List of patterns sorted by frequency (most common first)
        """
        if min_occurrences is None:
            min_occurrences = settings.pattern_matching_min_occurrences

        # Query for multi-word patterns (contains space)
        query = '''
            SELECT DISTINCT normalized_term, occurrence_count
            FROM tag_mappings
            WHERE language = %s
              AND normalized_term LIKE %s
              AND occurrence_count >= %s
            ORDER BY occurrence_count DESC
        '''

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (language, '% %', min_occurrences))
                results = await cursor.fetchall()

        # Convert to sorted list (most frequent first)
        patterns = [term for term, count in results]

        logger.info(f"Extracted {len(patterns)} multi-word patterns for language '{language}'")
        return patterns

    async def get_all_patterns_by_language(
        self,
        min_occurrences: int = None
    ) -> Dict[str, List[str]]:
        """
        Get multi-word patterns for all supported languages.

        Args:
            min_occurrences: Minimum occurrence count

        Returns:
            Dictionary mapping language code to list of patterns
        """
        patterns_by_lang = {}

        for lang in settings.supported_languages:
            patterns = await self.extract_multiword_patterns(lang, min_occurrences)
            if patterns:
                patterns_by_lang[lang] = patterns

        total_patterns = sum(len(p) for p in patterns_by_lang.values())
        logger.info(f"Loaded {total_patterns} total multi-word patterns across {len(patterns_by_lang)} languages")

        return patterns_by_lang


# Global instance
pattern_extractor = PatternExtractor()
