"""Processor using spaCy tokenization with pattern matching."""

from typing import Optional, List
from collections import defaultdict
from app.models.schemas import TokenizeResponse, TokenTag
from app.services.spacy_tokenizer import custom_tokenizer
from app.db.manager import dictionary_manager
from app.core.config import settings
import time
import logging

logger = logging.getLogger(__name__)


class SpacyProcessor:
    """Processor using spaCy tokenization with learned patterns."""

    async def initialize(self):
        """Initialize spaCy tokenizer with learned patterns."""
        await custom_tokenizer.initialize()

    async def try_spacy_pattern_match(
        self,
        keyword: str,
        language: str,
        start_time: float
    ) -> Optional[TokenizeResponse]:
        """
        Try to match keyword using spaCy tokenization + pattern lookup.

        Uses spaCy with learned multi-word patterns to tokenize, then looks up
        each token in tag_mappings. Only returns a result if ALL tokens are
        found with high confidence.

        Args:
            keyword: Keyword to process
            language: Language code
            start_time: Processing start time

        Returns:
            TokenizeResponse if all tokens matched, None otherwise (fall back to LLM)
        """
        # Tokenize with spaCy (using learned patterns)
        tokens = custom_tokenizer.tokenize(keyword, language)

        if not tokens:
            logger.warning(f"spaCy returned no tokens for '{keyword}'")
            return None

        logger.debug(f"spaCy tokenized '{keyword}' into: {tokens}")

        # Try to match all tokens against high-confidence patterns
        matched_tokens = []

        for token in tokens:
            # Look up high-confidence pattern
            pattern = await dictionary_manager.lookup_high_confidence_pattern(
                token, language
            )

            if not pattern:
                # Token not found or doesn't meet confidence criteria
                # Must fall back to LLM
                logger.debug(f"Token '{token}' not found in high-confidence patterns, falling back to LLM")
                return None

            # Convert pattern results to tags
            tags = [tag_type for tag_type, _ in pattern]
            # Use the highest confidence from all tag types
            max_confidence = max(conf for _, conf in pattern)

            matched_tokens.append(
                TokenTag(
                    token=token,
                    tags=sorted(tags),
                    confidence=round(max_confidence, 3),
                )
            )

        # All tokens matched! Construct response from patterns
        logger.info(f"All tokens matched for '{keyword}' using spaCy, skipping LLM")

        tag_summary = self._build_tag_summary(matched_tokens)
        processing_time = (time.time() - start_time) * 1000

        response = TokenizeResponse(
            original_keyword=keyword,
            language=language,
            tokens=tokens,
            tagged_tokens=matched_tokens,
            tag_summary=tag_summary,
            processing_time_ms=round(processing_time, 2),
            cache_hit=False,
            pattern_matched=True,
        )

        return response

    def _build_tag_summary(self, tokens: List[TokenTag]) -> dict[str, list[str]]:
        """Build a summary of tokens grouped by tag type."""
        summary = defaultdict(list)
        for token in tokens:
            for tag in token.tags:
                if token.token not in summary[tag]:
                    summary[tag].append(token.token)
        return dict(summary)


# Global instance
spacy_processor = SpacyProcessor()
