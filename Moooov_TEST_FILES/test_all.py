"""
Comprehensive testing script for keywords.csv dataset.
Tests all keywords against the tokenization API and generates detailed reports.

Usage:
    python test_all.py [options]

Options:
    --limit N          Test only first N keywords (default: all)
    --batch-size N     Batch size for API calls (default: 10)
    --api-url URL      API endpoint (default: http://localhost:8000)
    --output FILE      Output file for results (default: test_results.json)
    --no-cache         Disable cache for testing
"""

import csv
import json
import sys
import time
import asyncio
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import httpx
from tqdm import tqdm


def load_csv(filepath: str) -> List[Dict[str, str]]:
    """Load CSV with proper encoding detection."""
    encodings = ['utf-8', 'utf-8-sig', 'shift-jis', 'gbk', 'gb2312', 'euc-kr', 'cp1252', 'latin1']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                data = list(reader)
                print(f"✓ Successfully loaded {len(data):,} keywords with encoding: {encoding}")
                return data
        except (UnicodeDecodeError, UnicodeError):
            continue

    print("Could not decode file with any known encoding")
    return []


async def test_keyword(
    client: httpx.AsyncClient,
    keyword: str,
    language: str,
    api_url: str,
    use_cache: bool = True,
    use_spacy: bool = False
) -> Dict[str, Any]:
    """Test a single keyword against the API."""
    try:
        response = await client.post(
            f"{api_url}/api/v1/tokenize",
            json={
                "keyword": keyword,
                "language": language,
                "use_cache": use_cache,
                "learn_patterns": True,
                "use_spacy": use_spacy
            },
            timeout=30.0
        )

        if response.status_code == 200:
            return {
                "success": True,
                "keyword": keyword,
                "language": language,
                "data": response.json(),
                "status_code": 200,
                "error": None
            }
        else:
            return {
                "success": False,
                "keyword": keyword,
                "language": language,
                "data": None,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }

    except Exception as e:
        return {
            "success": False,
            "keyword": keyword,
            "language": language,
            "data": None,
            "status_code": None,
            "error": str(e)
        }


async def test_batch(
    keywords: List[Dict[str, str]],
    api_url: str,
    batch_size: int = 10,
    use_cache: bool = True,
    use_spacy: bool = False,
    show_progress: bool = True
) -> List[Dict[str, Any]]:
    """Test a batch of keywords with progress tracking."""
    results = []

    async with httpx.AsyncClient() as client:
        # Create progress bar
        pbar = tqdm(total=len(keywords), desc="Testing keywords", disable=not show_progress)

        # Process in batches
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]

            # Create tasks for concurrent execution
            tasks = [
                test_keyword(
                    client,
                    row['search_term'],
                    row.get('language', 'auto'),
                    api_url,
                    use_cache,
                    use_spacy
                )
                for row in batch
            ]

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            # Update progress
            pbar.update(len(batch))

            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.1)

        pbar.close()

    return results


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze test results and generate statistics."""
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total - successful

    # Success rate by language
    lang_success = defaultdict(lambda: {'total': 0, 'success': 0})
    for r in results:
        lang = r['language']
        lang_success[lang]['total'] += 1
        if r['success']:
            lang_success[lang]['success'] += 1

    # Processing time statistics (for successful results)
    processing_times = []
    cache_hits = 0
    cache_misses = 0
    pattern_matches = 0
    llm_calls = 0

    for r in results:
        if r['success'] and r['data']:
            processing_times.append(r['data']['processing_time_ms'])
            if r['data'].get('cache_hit'):
                cache_hits += 1
            else:
                cache_misses += 1

            # Track pattern matching vs LLM calls
            if r['data'].get('pattern_matched'):
                pattern_matches += 1
            elif not r['data'].get('cache_hit'):
                # Not cached and not pattern matched = LLM call
                llm_calls += 1

    avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
    min_time = min(processing_times) if processing_times else 0
    max_time = max(processing_times) if processing_times else 0

    # Tag distribution
    tag_counts = Counter()
    token_counts = []

    for r in results:
        if r['success'] and r['data']:
            tokens = r['data'].get('tagged_tokens', [])
            token_counts.append(len(tokens))
            for token in tokens:
                for tag in token.get('tags', []):
                    tag_counts[tag] += 1

    # Error analysis
    error_types = Counter()
    for r in results:
        if not r['success']:
            error = r.get('error', 'Unknown error')
            # Extract error type
            if 'HTTP' in error:
                error_type = error.split(':')[0]
            else:
                error_type = error.split(':')[0] if ':' in error else error[:50]
            error_types[error_type] += 1

    return {
        'summary': {
            'total_keywords': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0
        },
        'performance': {
            'avg_processing_time_ms': round(avg_time, 2),
            'min_processing_time_ms': round(min_time, 2),
            'max_processing_time_ms': round(max_time, 2),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0,
            'pattern_matches': pattern_matches,
            'llm_calls': llm_calls,
            'pattern_match_rate': (pattern_matches / (pattern_matches + llm_calls) * 100) if (pattern_matches + llm_calls) > 0 else 0
        },
        'language_stats': {
            lang: {
                'total': stats['total'],
                'success': stats['success'],
                'success_rate': (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            }
            for lang, stats in lang_success.items()
        },
        'token_stats': {
            'avg_tokens_per_keyword': sum(token_counts) / len(token_counts) if token_counts else 0,
            'min_tokens': min(token_counts) if token_counts else 0,
            'max_tokens': max(token_counts) if token_counts else 0
        },
        'tag_distribution': dict(tag_counts.most_common()),
        'errors': dict(error_types.most_common())
    }


def print_report(stats: Dict[str, Any]):
    """Print formatted analysis report."""
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    summary = stats['summary']
    print(f"\nSuccess Rate: {summary['success_rate']:.2f}%")
    print(f"   Total: {summary['total_keywords']:,}")
    print(f"   Successful: {summary['successful']:,}")
    print(f"   Failed: {summary['failed']:,}")

    perf = stats['performance']
    print(f"\nPerformance Metrics:")
    print(f"   Average processing time: {perf['avg_processing_time_ms']:.2f} ms")
    print(f"   Min/Max time: {perf['min_processing_time_ms']:.2f} / {perf['max_processing_time_ms']:.2f} ms")
    print(f"   Cache hit rate: {perf['cache_hit_rate']:.2f}% ({perf['cache_hits']} hits, {perf['cache_misses']} misses)")
    if perf.get('pattern_matches', 0) > 0 or perf.get('llm_calls', 0) > 0:
        print(f"   Pattern match rate: {perf['pattern_match_rate']:.2f}% ({perf['pattern_matches']} pattern, {perf['llm_calls']} LLM)")

    print(f"\nSuccess Rate by Language:")
    for lang, lang_stats in sorted(stats['language_stats'].items()):
        print(f"   {lang}: {lang_stats['success_rate']:.1f}% ({lang_stats['success']}/{lang_stats['total']})")

    token_stats = stats['token_stats']
    print(f"\nToken Statistics:")
    print(f"   Average tokens per keyword: {token_stats['avg_tokens_per_keyword']:.1f}")
    print(f"   Min/Max tokens: {token_stats['min_tokens']} / {token_stats['max_tokens']}")

    print(f"\n Tag Distribution (Top 10):")
    for tag, count in list(stats['tag_distribution'].items())[:10]:
        print(f"   {tag}: {count:,}")

    if stats['errors']:
        print(f"\n❌ Errors (Top 5):")
        for error, count in list(stats['errors'].items())[:5]:
            print(f"   {error}: {count}")

    print("\n" + "=" * 80)


def save_results(results: List[Dict[str, Any]], stats: Dict[str, Any], output_file: str):
    """Save detailed results to JSON file."""
    output_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_keywords': len(results)
        },
        'statistics': stats,
        'results': results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {output_file}")


def save_failed_keywords(results: List[Dict[str, Any]], output_file: str = "failed_keywords.csv"):
    """Save failed keywords to CSV for further investigation."""
    failed = [r for r in results if not r['success']]

    if not failed:
        print("\n✅ No failed keywords to save!")
        return

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['keyword', 'language', 'status_code', 'error'])

        for r in failed:
            writer.writerow([
                r['keyword'],
                r['language'],
                r['status_code'] or 'N/A',
                r['error'] or 'N/A'
            ])

    print(f"Failed keywords saved to: {output_file}")


async def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description='Test all keywords in keywords.csv')
    parser.add_argument('--limit', type=int, default=None, help='Test only first N keywords')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for API calls')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API endpoint URL')
    parser.add_argument('--output', default='test_results.json', help='Output file for results')
    parser.add_argument('--no-cache', action='store_true', help='Disable cache for testing')
    parser.add_argument('--use-spacy', action='store_true', help='Enable spaCy-based tokenization with learned patterns (skip LLM for high-confidence patterns)')
    parser.add_argument('--csv', default='keywords.csv', help='Input CSV file')

    args = parser.parse_args()

    # Load keywords
    print(f"Loading keywords from {args.csv}...")
    keywords = load_csv(args.csv)

    if not keywords:
        print("No keywords loaded. Exiting.")
        sys.exit(1)

    # Limit if specified
    if args.limit:
        keywords = keywords[:args.limit]
        print(f"Limited to first {args.limit} keywords")

    # Show configuration
    print(f"\nConfiguration:")
    print(f"   API URL: {args.api_url}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Use cache: {not args.no_cache}")
    print(f"   Use spaCy: {args.use_spacy}")
    print(f"   Total keywords: {len(keywords):,}")

    # Run tests
    print(f"\nStarting tests...\n")
    start_time = time.time()

    results = await test_batch(
        keywords,
        args.api_url,
        batch_size=args.batch_size,
        use_cache=not args.no_cache,
        use_spacy=args.use_spacy
    )

    elapsed = time.time() - start_time

    # Analyze results
    print(f"\nAnalyzing results...")
    stats = analyze_results(results)

    # Add timing information
    stats['performance']['total_elapsed_seconds'] = round(elapsed, 2)
    stats['performance']['keywords_per_second'] = round(len(results) / elapsed, 2) if elapsed > 0 else 0

    # Print report
    print_report(stats)
    print(f"\nTotal time: {elapsed:.2f}s ({stats['performance']['keywords_per_second']:.2f} keywords/sec)")

    # Save results
    save_results(results, stats, args.output)
    save_failed_keywords(results)

    print("\nTesting complete!")


if __name__ == '__main__':
    asyncio.run(main())
