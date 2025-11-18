"""Dictionary-only lookup tasks for fast processing."""

import asyncio
from typing import List, Dict, Any
from app.tasks.celery_app import celery_app
from app.db.manager import dictionary_manager


@celery_app.task(name="tasks.dictionary_lookup", bind=True)
def dictionary_lookup_task(self, keyword: str, language: str) -> Dict[str, Any]:
    """
    Perform dictionary-only lookup (fast, no LLM).

    This is a lightweight task that runs in the dictionary worker pool.
    It performs simple tokenization and enriches with dictionary lookups.

    Args:
        keyword: The keyword to process
        language: Language code

    Returns:
        Dict with tokens and processing metadata
    """
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(_dictionary_lookup_async(keyword, language))
    # Don't close the loop to avoid "Event loop is closed" errors
    # The loop will be garbage collected
    return result


async def _dictionary_lookup_async(keyword: str, language: str) -> Dict[str, Any]:
    """Async implementation of dictionary lookup."""
    # Simple tokenization by whitespace
    tokens = keyword.split()

    # Enrich with dictionaries
    enriched_tokens = []
    for token in tokens:
        # Normalize term (handles synonyms)
        normalized = await dictionary_manager.normalize_term(token, language)

        # Lookup in all dictionaries
        tags = []
        confidence = 0.5

        # Check each dictionary
        brand_conf = await dictionary_manager.lookup_brand(normalized, language)
        if brand_conf:
            tags.append("brand_term")
            confidence = max(confidence, brand_conf)

        product_conf = await dictionary_manager.lookup_product(normalized, language)
        if product_conf:
            tags.append("product_term")
            confidence = max(confidence, product_conf)

        color_conf = await dictionary_manager.lookup_color(normalized, language)
        if color_conf:
            tags.append("color_term")
            confidence = max(confidence, color_conf)

        audience_conf = await dictionary_manager.lookup_audience(normalized, language)
        if audience_conf:
            tags.append("audience_term")
            confidence = max(confidence, audience_conf)

        scenario_conf = await dictionary_manager.lookup_scenario(normalized, language)
        if scenario_conf:
            tags.append("scenario_term")
            confidence = max(confidence, scenario_conf)

        sp_conf = await dictionary_manager.lookup_selling_point(normalized, language)
        if sp_conf:
            tags.append("selling_point_term")
            confidence = max(confidence, sp_conf)

        attr_conf = await dictionary_manager.lookup_attribute(normalized, language)
        if attr_conf:
            tags.append("attribute_term")
            confidence = max(confidence, attr_conf)

        # Check learned patterns
        learned = await dictionary_manager.lookup_learned_tags(normalized, language)
        for tag_type, conf in learned:
            if tag_type not in tags:
                tags.append(tag_type)
            confidence = max(confidence, conf)

        enriched_tokens.append(
            {
                "token": token,
                "tags": tags or ["unknown"],
                "confidence": round(confidence, 3),
            }
        )

    return {
        "keyword": keyword,
        "language": language,
        "tokens": enriched_tokens,
        "processing_path": "dictionary",
    }
