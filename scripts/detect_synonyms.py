"""Detect synonyms from learned patterns using LLM."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict
from openai import AsyncOpenAI

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_pool, close_pool
from app.core.config import settings


SYNONYM_DETECTION_PROMPT = """You are an e-commerce terminology expert specializing in identifying synonyms.

Task: Given this list of {count} e-commerce product terms in {language}, identify groups of synonyms.

CRITICAL RULES:
1. Only group terms that have the EXACT SAME meaning in product contexts
2. Terms must be true synonyms, not just related words
3. Choose the most common/standard term as the canonical_term
4. Only include high-confidence matches (>0.85)
5. If no synonyms found, return empty array

Terms:
{term_list}

Return a JSON object with this exact structure:
{{
  "synonym_groups": [
    {{
      "canonical_term": "smartphone",
      "synonyms": ["cell phone", "mobile phone"],
      "confidence": 0.95
    }}
  ]
}}

Examples of VALID synonyms:
- "smartphone", "cell phone", "mobile phone" (same product)
- "t-shirt", "tee" (same item)
- "sneakers", "trainers", "athletic shoes" (same category)

Examples of INVALID (don't group):
- "phone" and "smartphone" (different - one is more specific)
- "shoes" and "sneakers" (different - one is category, one is type)
- "red" and "blue" (related but not synonyms)

Language: {language}
"""


async def fetch_top_terms(language: str, limit: int = 1000) -> List[tuple]:
    """Fetch top N terms from tag_mappings by occurrence count."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT DISTINCT normalized_term, SUM(occurrence_count) as total_count
                FROM tag_mappings
                WHERE language = %s
                GROUP BY normalized_term
                ORDER BY total_count DESC
                LIMIT %s
                """,
                (language, limit),
            )
            return await cursor.fetchall()


async def detect_synonyms_batch(
    terms: List[str], language: str, client: AsyncOpenAI
) -> List[Dict]:
    """Detect synonyms for a batch of terms using LLM."""
    lang_names = {
        "zh": "Chinese",
        "en": "English",
        "es": "Spanish",
        "ja": "Japanese",
        "de": "German",
        "fr": "French",
        "ko": "Korean",
        "pt": "Portuguese",
        "id": "Indonesian",
        "ru": "Russian",
    }

    term_list = "\n".join([f"- {term}" for term in terms])
    prompt = SYNONYM_DETECTION_PROMPT.format(
        count=len(terms),
        language=lang_names.get(language, language),
        term_list=term_list,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        return data.get("synonym_groups", [])

    except Exception as e:
        print(f"Error detecting synonyms: {e}")
        return []


async def save_synonym_mappings(synonym_groups: List[Dict], language: str) -> int:
    """Save synonym mappings to database."""
    pool = await get_pool()
    saved_count = 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for group in synonym_groups:
                canonical_term = group.get("canonical_term", "").lower()
                synonyms = group.get("synonyms", [])
                confidence = group.get("confidence", 1.0)

                if not canonical_term or not synonyms:
                    continue

                # Insert each synonym mapping
                for synonym in synonyms:
                    synonym_lower = synonym.lower()
                    try:
                        await cursor.execute(
                            """
                            INSERT INTO synonym_mappings (canonical_term, synonym_term, language, confidence)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                canonical_term = %s,
                                confidence = %s
                            """,
                            (
                                canonical_term,
                                synonym_lower,
                                language,
                                confidence,
                                canonical_term,
                                confidence,
                            ),
                        )
                        saved_count += 1
                    except Exception as e:
                        print(f"Error saving synonym '{synonym_lower}': {e}")

            await conn.commit()

    return saved_count


async def main():
    """Main function to detect and save synonyms."""
    print("Synonym Detection Script")
    print("=" * 50)
    print()

    # Get parameters
    languages = settings.supported_languages
    top_n = 1000  # Fetch top 1000 words per language
    batch_size = 100  # Process 100 words at a time

    # Initialize LLM client
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url
    )

    try:
        for language in languages:
            print(f"Processing language: {language}")
            print("-" * 50)

            # Fetch top terms
            print(f"  Fetching top {top_n} terms...")
            terms_data = await fetch_top_terms(language, top_n)

            if not terms_data:
                print(f"  No terms found for {language}")
                print()
                continue

            terms = [term[0] for term in terms_data]
            print(f"  Found {len(terms)} terms")

            # Process in batches
            total_groups = 0
            total_saved = 0

            for i in range(0, len(terms), batch_size):
                batch = terms[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(terms) + batch_size - 1) // batch_size

                print(
                    f"  Processing batch {batch_num}/{total_batches} ({len(batch)} terms)..."
                )

                # Detect synonyms
                synonym_groups = await detect_synonyms_batch(batch, language, client)

                if synonym_groups:
                    print(f"    Found {len(synonym_groups)} synonym groups")
                    # Save to database
                    saved = await save_synonym_mappings(synonym_groups, language)
                    total_saved += saved
                    total_groups += len(synonym_groups)
                else:
                    print(f"    No synonyms found in this batch")

                # Small delay to avoid rate limiting
                await asyncio.sleep(1)

            print(f"  ✓ Completed {language}")
            print(f"    Total synonym groups: {total_groups}")
            print(f"    Total mappings saved: {total_saved}")
            print()

        print("=" * 50)
        print("✓ Synonym detection completed for all languages!")
        print()
        print("Next steps:")
        print("  1. Review synonym_mappings table in database")
        print("  2. Run merge_synonyms.py to consolidate dictionaries")
        print("  3. Test tokenization to verify synonym normalization works")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
