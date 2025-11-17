"""LLM processing tasks for accurate tokenization."""

import asyncio
from typing import Dict, Any, Optional
from app.tasks.celery_app import celery_app
from app.services.llm_processor import llm_processor
from app.db.manager import dictionary_manager


@celery_app.task(name="tasks.llm_process", bind=True)
def llm_process_task(self, keyword: str, language: str) -> Dict[str, Any]:
    """
    Perform LLM-based tokenization (slow, accurate).

    This is a resource-intensive task that runs in the LLM worker pool.
    It uses the LLM for tokenization with retry logic and circuit breaker.

    Args:
        keyword: The keyword to process
        language: Language code

    Returns:
        Dict with tokens and processing metadata
    """
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(_llm_process_async(keyword, language))
        return result
    finally:
        loop.close()


async def _llm_process_async(keyword: str, language: str) -> Dict[str, Any]:
    """Async implementation of LLM processing."""
    try:
        # Process with LLM (includes retry + circuit breaker)
        tokens = await llm_processor.process(keyword, language)

        if not tokens:
            return {
                "keyword": keyword,
                "language": language,
                "error": "LLM returned no tokens",
                "processing_path": "llm_failed",
            }

        # Enrich with dictionaries
        enriched_tokens = []
        for token in tokens:
            # Get normalized term
            normalized = await dictionary_manager.normalize_term(
                token.token, language
            )

            tags = set(token.tags)
            confidence = token.confidence

            # Enrich with dictionary lookups
            brand_conf = await dictionary_manager.lookup_brand(normalized, language)
            if brand_conf:
                tags.add("brand_term")
                confidence = max(confidence, brand_conf)

            product_conf = await dictionary_manager.lookup_product(normalized, language)
            if product_conf:
                tags.add("product_term")
                confidence = max(confidence, product_conf)

            color_conf = await dictionary_manager.lookup_color(normalized, language)
            if color_conf:
                tags.add("color_term")
                confidence = max(confidence, color_conf)

            audience_conf = await dictionary_manager.lookup_audience(
                normalized, language
            )
            if audience_conf:
                tags.add("audience_term")
                confidence = max(confidence, audience_conf)

            scenario_conf = await dictionary_manager.lookup_scenario(
                normalized, language
            )
            if scenario_conf:
                tags.add("scenario_term")
                confidence = max(confidence, scenario_conf)

            sp_conf = await dictionary_manager.lookup_selling_point(
                normalized, language
            )
            if sp_conf:
                tags.add("selling_point_term")
                confidence = max(confidence, sp_conf)

            attr_conf = await dictionary_manager.lookup_attribute(normalized, language)
            if attr_conf:
                tags.add("attribute_term")
                confidence = max(confidence, attr_conf)

            learned = await dictionary_manager.lookup_learned_tags(
                normalized, language
            )
            for tag_type, conf in learned:
                tags.add(tag_type)
                confidence = max(confidence, conf)

            enriched_tokens.append(
                {
                    "token": token.token,
                    "tags": sorted(list(tags)),
                    "confidence": round(confidence, 3),
                }
            )

        return {
            "keyword": keyword,
            "language": language,
            "tokens": enriched_tokens,
            "processing_path": "llm",
        }

    except Exception as e:
        return {
            "keyword": keyword,
            "language": language,
            "error": str(e),
            "processing_path": "llm_error",
        }
