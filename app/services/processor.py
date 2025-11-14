"""Main keyword processing service."""

import asyncio
import time
from typing import Optional, List
from collections import defaultdict
from app.models.schemas import TokenizeResponse, TokenTag
from app.utils.language_detector import validate_language
from app.services.llm_processor import llm_processor
from app.services.cache import cache_service
from app.db.manager import dictionary_manager
from app.services.spacy_processor import spacy_processor
from app.core.config import settings
from app.utils.circuit_breaker import CircuitOpenError


# Stopwords for post-processing filter (backup safety net)
STOPWORDS = {
    "en": {
        "the", "a", "an", "and", "or", "for", "with", "in", "on", "at",
        "to", "from", "of", "by", "is", "are", "was", "were", "be",
    },
    "zh": {"的", "了", "在", "是", "和", "与", "或", "为", "以", "有"},
    "ja": {"の", "は", "を", "に", "が", "で", "と", "へ", "や", "か"},
    "de": {"der", "die", "das", "und", "oder", "für", "mit", "von", "zu", "ist"},
    "fr": {"le", "la", "les", "un", "une", "et", "ou", "de", "du", "des", "est"},
    "es": {"el", "la", "los", "las", "un", "una", "y", "o", "de", "del", "es"},
    "pt": {"o", "a", "os", "as", "um", "uma", "e", "ou", "de", "do", "é"},
    "id": {"yang", "dan", "atau", "untuk", "dengan", "dari", "ke", "adalah"},
    "ru": {"и", "или", "для", "с", "от", "к", "в", "на", "это"},
    "ko": {"의", "는", "을", "를", "이", "가", "에", "와", "과"},
}


class KeywordProcessor:
    """Main processor for keyword tokenization and tagging."""

    async def process(
        self,
        keyword: str,
        language: Optional[str] = None,
        use_cache: bool = True,
        learn_patterns: bool = True,
        use_spacy: bool = False,
    ) -> TokenizeResponse:
        """
        Process a keyword to extract tokens and semantic tags.

        Args:
            keyword: The keyword to process
            language: Language code (auto-detect if None)
            use_cache: Whether to use cache
            learn_patterns: Whether to learn new patterns
            use_spacy: Whether to use spaCy-based tokenization with learned patterns (skip LLM if all tokens match)

        Returns:
            TokenizeResponse with tokens, tags, and metadata
        """
        start_time = time.time()

        # Validate and detect language
        lang = validate_language(language, keyword)

        # Check cache
        if use_cache:
            cached = await cache_service.get(keyword, lang)
            if cached:
                # Update cache_hit flag and processing time for cached response
                processing_time = (time.time() - start_time) * 1000
                cached.cache_hit = True
                cached.processing_time_ms = round(processing_time, 2)
                return cached

        cache_hit = False
        pattern_matched = False
        processing_path = "unknown"

        # Try spaCy pattern matching if enabled (FAST PATH)
        if use_spacy:
            try:
                spacy_result = await spacy_processor.try_spacy_pattern_match(
                    keyword, lang, start_time
                )
                if spacy_result:
                    processing_path = "spacy"
                    # Cache and return spaCy result
                    if use_cache:
                        await cache_service.set(keyword, lang, spacy_result)
                    return spacy_result
            except Exception as e:
                print(f"spaCy processing failed: {e}")
                # Continue to LLM fallback

        # Try LLM processing with retry and circuit breaker
        tagged_tokens = None
        try:
            tagged_tokens = await llm_processor.process(keyword, lang)
            if tagged_tokens:
                processing_path = "llm"
                # Apply post-processing filter (safety net)
                tagged_tokens = self._post_filter_tokens(tagged_tokens, lang)

        except CircuitOpenError:
            # Circuit breaker is open - LLM service is down
            print(f"Circuit breaker open - using fallback for: {keyword}")
            processing_path = "fallback_circuit_open"

        except asyncio.TimeoutError:
            # All retries exhausted due to timeouts
            print(f"LLM timeout after all retries for: {keyword}")
            processing_path = "fallback_timeout"

        except Exception as e:
            # All retries exhausted due to other errors
            print(f"LLM failed after retries: {e}")
            processing_path = "fallback_error"

        # Fallback 1: Simple tokenization + dictionary enrichment
        if not tagged_tokens:
            print(f"Using simple tokenization fallback for: {keyword}")
            tagged_tokens = self._simple_tokenize(keyword, lang)
            processing_path = f"{processing_path}_simple_tokenize"

        # Fallback 2: If still no tokens, return keyword as single token
        if not tagged_tokens:
            tagged_tokens = [
                TokenTag(token=keyword, tags=["unknown"], confidence=0.1)
            ]
            processing_path = f"{processing_path}_single_token"

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
            pattern_matched=pattern_matched,
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

    def _post_filter_tokens(
        self, tokens: List[TokenTag], language: str
    ) -> List[TokenTag]:
        """
        Apply post-processing filters as safety net.

        This catches tokens that the LLM might have missed filtering.
        Filters out:
        - Very low confidence tokens (< 0.3)
        - Single characters (except for CJK languages)
        - Pure stopwords
        """
        filtered = []
        stopwords = STOPWORDS.get(language, set())
        is_cjk = language in ["zh", "ja", "ko"]

        for token in tokens:
            # Skip very low confidence tokens
            if token.confidence < 0.3:
                continue

            # Skip single chars for non-CJK languages
            if not is_cjk and len(token.token) == 1:
                continue

            # Skip pure stopwords (backup check)
            if token.token.lower() in stopwords:
                continue

            # Skip tokens that are only whitespace or punctuation
            if not token.token.strip() or token.token.strip() in ".,!?;:-_":
                continue

            filtered.append(token)

        return filtered

    def _simple_tokenize(self, keyword: str, language: str) -> List[TokenTag]:
        """
        Simple whitespace-based tokenization as fallback.

        Used when LLM processing fails completely. Splits by whitespace
        and creates tokens with low confidence.

        Args:
            keyword: The keyword to tokenize
            language: Language code

        Returns:
            List of TokenTag objects with low confidence
        """
        # Split by whitespace
        tokens = keyword.split()

        # Filter out stopwords and very short tokens
        stopwords = STOPWORDS.get(language, set())
        is_cjk = language in ["zh", "ja", "ko"]

        filtered_tokens = []
        for token in tokens:
            token_clean = token.strip()

            # Skip empty tokens
            if not token_clean:
                continue

            # Skip stopwords
            if token_clean.lower() in stopwords:
                continue

            # Skip single chars for non-CJK
            if not is_cjk and len(token_clean) == 1:
                continue

            # Create TokenTag with low confidence (will be enriched by dictionary)
            filtered_tokens.append(
                TokenTag(
                    token=token_clean,
                    tags=[],
                    confidence=0.4  # Low confidence for simple tokenization
                )
            )

        return filtered_tokens


# Global instance
keyword_processor = KeywordProcessor()
