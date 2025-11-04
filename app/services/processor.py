"""Main keyword processing service."""

import time
from typing import Optional
from collections import defaultdict
from app.models.schemas import TokenizeResponse, TokenTag
from app.utils.language_detector import validate_language
from app.services.llm_processor import llm_processor
from app.services.cache import cache_service
from app.db.manager import dictionary_manager
from app.core.config import settings


class KeywordProcessor:
    """Main processor for keyword tokenization and tagging."""

    async def process(
        self,
        keyword: str,
        language: Optional[str] = None,
        use_cache: bool = True,
        learn_patterns: bool = True,
    ) -> TokenizeResponse:
        """
        Process a keyword to extract tokens and semantic tags.

        Args:
            keyword: The keyword to process
            language: Language code (auto-detect if None)
            use_cache: Whether to use cache
            learn_patterns: Whether to learn new patterns

        Returns:
            TokenizeResponse with tokens, tags, and metadata
        """
        start_time = time.time()

        # Validate and detect language
        lang = validate_language(language, keyword)

        # Check cache
        cache_hit = False
        if use_cache:
            cached = await cache_service.get(keyword, lang)
            if cached:
                return cached

        # Process with LLM
        tagged_tokens = await llm_processor.process(keyword, lang)

        if not tagged_tokens:
            # Fallback: return keyword as single token
            tagged_tokens = [
                TokenTag(token=keyword, tags=[], confidence=0.5)
            ]

        # Enrich with dictionary lookups
        enriched_tokens = await self._enrich_with_dictionaries(tagged_tokens, lang)

        # Learn patterns if enabled
        if learn_patterns:
            await self._learn_patterns(enriched_tokens, lang)

        # Build response
        tokens = [t.token for t in enriched_tokens]
        tag_summary = self._build_tag_summary(enriched_tokens)
        processing_time = (time.time() - start_time) * 1000

        response = TokenizeResponse(
            original_keyword=keyword,
            language=lang,
            tokens=tokens,
            tagged_tokens=enriched_tokens,
            tag_summary=tag_summary,
            processing_time_ms=round(processing_time, 2),
            cache_hit=cache_hit,
        )

        # Cache the result
        if use_cache:
            await cache_service.set(keyword, lang, response)

        return response

    async def _enrich_with_dictionaries(
        self, tokens: list[TokenTag], language: str
    ) -> list[TokenTag]:
        """
        Enrich tokens with dictionary lookups.

        Adds tags from pre-defined dictionaries and learned patterns.
        """
        enriched = []

        for token in tokens:
            tags = set(token.tags)
            max_confidence = token.confidence

            # Check brand dictionary
            brand_conf = await dictionary_manager.lookup_brand(token.token, language)
            if brand_conf:
                tags.add("brand_term")
                max_confidence = max(max_confidence, brand_conf)

            # Check product dictionary
            product_conf = await dictionary_manager.lookup_product(token.token, language)
            if product_conf:
                tags.add("product_term")
                max_confidence = max(max_confidence, product_conf)

            # Check color dictionary
            color_conf = await dictionary_manager.lookup_color(token.token, language)
            if color_conf:
                tags.add("color_term")
                max_confidence = max(max_confidence, color_conf)

            # Check audience dictionary
            audience_conf = await dictionary_manager.lookup_audience(token.token, language)
            if audience_conf:
                tags.add("audience_term")
                max_confidence = max(max_confidence, audience_conf)

            # Check scenario dictionary
            scenario_conf = await dictionary_manager.lookup_scenario(token.token, language)
            if scenario_conf:
                tags.add("scenario_term")
                max_confidence = max(max_confidence, scenario_conf)

            # Check selling point dictionary
            sp_conf = await dictionary_manager.lookup_selling_point(token.token, language)
            if sp_conf:
                tags.add("selling_point_term")
                max_confidence = max(max_confidence, sp_conf)

            # Check attribute dictionary
            attr_conf = await dictionary_manager.lookup_attribute(token.token, language)
            if attr_conf:
                tags.add("attribute_term")
                max_confidence = max(max_confidence, attr_conf)

            # Check learned patterns
            learned = await dictionary_manager.lookup_learned_tags(token.token, language)
            for tag_type, conf in learned:
                tags.add(tag_type)
                max_confidence = max(max_confidence, conf)

            enriched.append(
                TokenTag(
                    token=token.token,
                    tags=sorted(list(tags)),
                    confidence=round(max_confidence, 3),
                )
            )

        return enriched

    async def _learn_patterns(
        self, tokens: list[TokenTag], language: str
    ) -> None:
        """Learn patterns from high-confidence tokens."""
        if not settings.enable_learning:
            return

        for token in tokens:
            if token.confidence >= settings.learning_confidence_threshold:
                for tag in token.tags:
                    await dictionary_manager.add_learned_pattern(
                        token.token, tag, language, token.confidence
                    )

    def _build_tag_summary(self, tokens: list[TokenTag]) -> dict[str, list[str]]:
        """Build a summary of tokens grouped by tag type."""
        summary = defaultdict(list)
        for token in tokens:
            for tag in token.tags:
                if token.token not in summary[tag]:
                    summary[tag].append(token.token)
        return dict(summary)


# Global instance
keyword_processor = KeywordProcessor()
