"""Merge synonyms in dictionary tables based on synonym mappings."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_pool, close_pool
from app.core.config import settings


# Dictionary tables to update
DICTIONARY_TABLES = [
    ("brands", "normalized_name"),
    ("product_terms", "normalized_term"),
    ("color_terms", "normalized_term"),
    ("audience_terms", "normalized_term"),
    ("scenario_terms", "normalized_term"),
    ("selling_point_terms", "normalized_term"),
    ("attribute_terms", "normalized_term"),
]


async def fetch_synonym_mappings() -> List[tuple]:
    """Fetch all synonym mappings from database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT canonical_term, synonym_term, language, confidence
                FROM synonym_mappings
                ORDER BY language, canonical_term
                """
            )
            return await cursor.fetchall()


async def merge_dictionary_table(
    table_name: str, term_column: str, synonym_map: Dict[tuple, str]
) -> Dict[str, int]:
    """
    Merge synonyms in a dictionary table.

    Args:
        table_name: Name of the dictionary table
        term_column: Name of the term column (normalized_name or normalized_term)
        synonym_map: Dict mapping (term, language) -> canonical_term

    Returns:
        Dict with statistics (updated, deleted, errors)
    """
    pool = await get_pool()
    stats = {"updated": 0, "deleted": 0, "errors": 0}

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Fetch all terms from this table
            await cursor.execute(
                f"SELECT {term_column}, language FROM {table_name}"
            )
            terms = await cursor.fetchall()

            for term, language in terms:
                key = (term, language)
                if key in synonym_map:
                    canonical_term = synonym_map[key]

                    if canonical_term == term:
                        continue  # Already canonical

                    try:
                        # Update to canonical term
                        await cursor.execute(
                            f"""
                            UPDATE {table_name}
                            SET {term_column} = %s
                            WHERE {term_column} = %s AND language = %s
                            """,
                            (canonical_term, term, language),
                        )
                        stats["updated"] += 1

                    except Exception as e:
                        # Likely duplicate key error - delete the synonym entry
                        try:
                            await cursor.execute(
                                f"""
                                DELETE FROM {table_name}
                                WHERE {term_column} = %s AND language = %s
                                """,
                                (term, language),
                            )
                            stats["deleted"] += 1
                        except Exception as delete_error:
                            print(
                                f"  Error processing {term} in {table_name}: {delete_error}"
                            )
                            stats["errors"] += 1

            await conn.commit()

    return stats


async def merge_tag_mappings(synonym_map: Dict[tuple, str]) -> Dict[str, int]:
    """
    Merge synonyms in tag_mappings table and consolidate occurrence counts.

    For each synonym group:
    1. Sum up occurrence counts
    2. Keep highest confidence
    3. Update to canonical term
    4. Delete duplicate entries
    """
    pool = await get_pool()
    stats = {"merged": 0, "deleted": 0, "errors": 0}

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Group synonyms by (canonical_term, tag_type, language)
            canonical_groups: Dict[tuple, List[tuple]] = {}

            for (term, language), canonical in synonym_map.items():
                # Fetch all tag mappings for this synonym
                await cursor.execute(
                    """
                    SELECT normalized_term, tag_type, language, confidence, occurrence_count
                    FROM tag_mappings
                    WHERE normalized_term = %s AND language = %s
                    """,
                    (term, language),
                )
                mappings = await cursor.fetchall()

                for mapping in mappings:
                    norm_term, tag_type, lang, conf, occ_count = mapping
                    key = (canonical, tag_type, lang)

                    if key not in canonical_groups:
                        canonical_groups[key] = []

                    canonical_groups[key].append(
                        {
                            "original_term": norm_term,
                            "confidence": conf,
                            "occurrence_count": occ_count,
                        }
                    )

            # Process each canonical group
            for (canonical_term, tag_type, language), group in canonical_groups.items():
                if len(group) <= 1:
                    # Only one term in this group, just update if needed
                    if (
                        group[0]["original_term"] != canonical_term
                        and group[0]["original_term"] in [
                            k[0] for k in synonym_map.keys()
                        ]
                    ):
                        try:
                            await cursor.execute(
                                """
                                UPDATE tag_mappings
                                SET normalized_term = %s
                                WHERE normalized_term = %s AND tag_type = %s AND language = %s
                                """,
                                (
                                    canonical_term,
                                    group[0]["original_term"],
                                    tag_type,
                                    language,
                                ),
                            )
                            stats["merged"] += 1
                        except:
                            pass
                    continue

                # Multiple terms in group - need to consolidate
                total_occurrences = sum(item["occurrence_count"] for item in group)
                max_confidence = max(item["confidence"] for item in group)

                # Check if canonical term already exists
                canonical_exists = any(
                    item["original_term"] == canonical_term for item in group
                )

                try:
                    if canonical_exists:
                        # Update existing canonical entry
                        await cursor.execute(
                            """
                            UPDATE tag_mappings
                            SET occurrence_count = %s, confidence = %s
                            WHERE normalized_term = %s AND tag_type = %s AND language = %s
                            """,
                            (total_occurrences, max_confidence, canonical_term, tag_type, language),
                        )

                        # Delete synonym entries
                        for item in group:
                            if item["original_term"] != canonical_term:
                                await cursor.execute(
                                    """
                                    DELETE FROM tag_mappings
                                    WHERE normalized_term = %s AND tag_type = %s AND language = %s
                                    """,
                                    (item["original_term"], tag_type, language),
                                )
                                stats["deleted"] += 1

                    else:
                        # Create new canonical entry and delete all synonyms
                        await cursor.execute(
                            """
                            INSERT INTO tag_mappings (normalized_term, tag_type, language, confidence, occurrence_count)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                occurrence_count = %s,
                                confidence = %s
                            """,
                            (
                                canonical_term,
                                tag_type,
                                language,
                                max_confidence,
                                total_occurrences,
                                total_occurrences,
                                max_confidence,
                            ),
                        )

                        # Delete all synonym entries
                        for item in group:
                            await cursor.execute(
                                """
                                DELETE FROM tag_mappings
                                WHERE normalized_term = %s AND tag_type = %s AND language = %s
                                """,
                                (item["original_term"], tag_type, language),
                            )
                            stats["deleted"] += 1

                    stats["merged"] += 1

                except Exception as e:
                    print(
                        f"  Error merging tag_mappings for {canonical_term}/{tag_type}/{language}: {e}"
                    )
                    stats["errors"] += 1

            await conn.commit()

    return stats


async def main():
    """Main function to merge synonyms across all tables."""
    print("Synonym Merging Script")
    print("=" * 50)
    print()

    try:
        # Fetch synonym mappings
        print("Fetching synonym mappings...")
        mappings = await fetch_synonym_mappings()

        if not mappings:
            print("No synonym mappings found. Run detect_synonyms.py first.")
            return

        # Build synonym map: (term, language) -> canonical_term
        synonym_map: Dict[tuple, str] = {}
        for canonical, synonym, language, confidence in mappings:
            synonym_map[(synonym, language)] = canonical

        print(f"Found {len(synonym_map)} synonym mappings")
        print()

        # Process tag_mappings table first (most important)
        print("Merging tag_mappings table...")
        tag_stats = await merge_tag_mappings(synonym_map)
        print(f"  ✓ Merged: {tag_stats['merged']}")
        print(f"  ✓ Deleted: {tag_stats['deleted']}")
        if tag_stats["errors"] > 0:
            print(f"  ✗ Errors: {tag_stats['errors']}")
        print()

        # Process dictionary tables
        total_updated = 0
        total_deleted = 0
        total_errors = 0

        for table_name, term_column in DICTIONARY_TABLES:
            print(f"Merging {table_name}...")
            stats = await merge_dictionary_table(table_name, term_column, synonym_map)
            print(f"  ✓ Updated: {stats['updated']}")
            print(f"  ✓ Deleted: {stats['deleted']}")
            if stats["errors"] > 0:
                print(f"  ✗ Errors: {stats['errors']}")

            total_updated += stats["updated"]
            total_deleted += stats["deleted"]
            total_errors += stats["errors"]

        print()
        print("=" * 50)
        print("✓ Synonym merging completed!")
        print()
        print("Summary:")
        print(f"  Tag mappings merged: {tag_stats['merged']}")
        print(f"  Dictionary entries updated: {total_updated}")
        print(f"  Duplicate entries removed: {total_deleted + tag_stats['deleted']}")
        if total_errors + tag_stats["errors"] > 0:
            print(f"  Errors encountered: {total_errors + tag_stats['errors']}")
        print()
        print("Next steps:")
        print("  1. Verify dictionary tables have canonical terms")
        print("  2. Test tokenization to confirm synonym normalization works")
        print("  3. Monitor for any issues in production")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
