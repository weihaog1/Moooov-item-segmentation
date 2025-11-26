"""Dictionary-only lookup tasks for fast processing."""

import asyncio
from typing import Dict, Any
from app.tasks.celery_app import celery_app
from app.core.config import settings
import pymysql


@celery_app.task(name="tasks.dictionary_lookup", bind=True)
def dictionary_lookup_task(self, keyword: str, language: str) -> Dict[str, Any]:
    """
    Perform dictionary lookup with optional LLM fallback.

    Behavior depends on USE_LLM_FIRST setting:
    - If True: This shouldn't be called (LLM task is used instead)
    - If False: Dictionary first, fallback to LLM if unknowns found

    This is a lightweight task that runs in the dictionary worker pool.
    It performs simple tokenization and enriches with dictionary lookups.

    Args:
        keyword: The keyword to tokenize
        language: Language code

    Returns:
        Dict with tokens and processing metadata
    """
    # Simple tokenization by whitespace
    tokens = keyword.split()

    # Create synchronous MySQL connection for this task
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        enriched_tokens = []

        with conn.cursor() as cursor:
            for token in tokens:
                normalized = token.lower()
                tags = []
                confidence = 0.5

                # Check synonym mapping first
                cursor.execute(
                    "SELECT canonical_term FROM synonym_mappings WHERE synonym_term = %s AND language = %s",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    normalized = result['canonical_term']

                # Check each dictionary
                cursor.execute(
                    "SELECT confidence FROM brands WHERE normalized_name = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("brand_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM product_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("product_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM color_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("color_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM audience_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("audience_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM scenario_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("scenario_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM selling_point_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("selling_point_term")
                    confidence = max(confidence, result['confidence'])

                cursor.execute(
                    "SELECT confidence FROM attribute_terms WHERE normalized_term = %s AND language = %s LIMIT 1",
                    (normalized, language)
                )
                result = cursor.fetchone()
                if result:
                    tags.append("attribute_term")
                    confidence = max(confidence, result['confidence'])

                # Check learned patterns
                cursor.execute(
                    "SELECT tag_type, confidence FROM tag_mappings WHERE normalized_term = %s AND language = %s",
                    (normalized, language)
                )
                for row in cursor.fetchall():
                    if row['tag_type'] not in tags:
                        tags.append(row['tag_type'])
                    confidence = max(confidence, row['confidence'])

                enriched_tokens.append({
                    "token": token,
                    "tags": tags or ["unknown"],
                    "confidence": round(confidence, 3),
                })

        return {
            "keyword": keyword,
            "language": language,
            "tokens": enriched_tokens,
            "processing_path": "dictionary",
        }
    finally:
        conn.close()
