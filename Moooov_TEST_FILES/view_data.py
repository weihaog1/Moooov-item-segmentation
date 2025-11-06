"""
Simple script to view and analyze the keywords.csv test file.
Usage: python view_data.py
"""

import csv
import sys
from collections import Counter

def load_csv(filepath):
    """Load CSV with proper encoding detection."""
    encodings = ['utf-8', 'utf-8-sig', 'shift-jis', 'gbk', 'gb2312', 'euc-kr', 'cp1252', 'latin1']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                data = list(reader)
                print(f"✓ Successfully loaded with encoding: {encoding}\n")
                return data
        except (UnicodeDecodeError, UnicodeError):
            continue

    print("❌ Could not decode file with any known encoding")
    return None

def analyze_data(data):
    """Analyze and display data statistics."""
    if not data:
        return

    print("=" * 80)
    print("📊 DATASET OVERVIEW")
    print("=" * 80)
    print(f"Total records: {len(data):,}")

    # Language distribution
    languages = [row.get('language', 'unknown') for row in data]
    lang_count = Counter(languages)

    print(f"\n📝 Language Distribution:")
    for lang, count in lang_count.most_common():
        percentage = (count / len(data)) * 100
        print(f"  {lang}: {count:,} ({percentage:.1f}%)")

    # Keyword length statistics
    keyword_lengths = [len(row.get('search_term', '')) for row in data]
    avg_length = sum(keyword_lengths) / len(keyword_lengths)

    print(f"\n📏 Keyword Length Statistics:")
    print(f"  Average length: {avg_length:.1f} characters")
    print(f"  Shortest: {min(keyword_lengths)} characters")
    print(f"  Longest: {max(keyword_lengths)} characters")

    # Sample data
    print("\n" + "=" * 80)
    print("📋 SAMPLE DATA (First 20 records)")
    print("=" * 80)
    print(f"{'#':<5} {'Keyword':<60} {'Language':<10}")
    print("-" * 80)

    for i, row in enumerate(data[:20], 1):
        keyword = row.get('search_term', '')[:55]
        language = row.get('language', 'unknown')
        print(f"{i:<5} {keyword:<60} {language:<10}")

    # Show some examples by language
    print("\n" + "=" * 80)
    print("🌍 EXAMPLES BY LANGUAGE")
    print("=" * 80)

    for lang in lang_count.most_common(5):  # Show top 5 languages
        lang_name = lang[0]
        examples = [row.get('search_term', '') for row in data if row.get('language') == lang_name][:5]
        print(f"\n{lang_name} (showing {min(5, len(examples))} examples):")
        for i, example in enumerate(examples, 1):
            print(f"  {i}. {example}")

    # Search functionality
    print("\n" + "=" * 80)
    print("🔍 SEARCH FUNCTIONALITY")
    print("=" * 80)
    print("Commands:")
    print("  search <text>  - Search keywords containing text")
    print("  lang <code>    - Show keywords for specific language")
    print("  stats          - Show statistics again")
    print("  quit           - Exit")

    return data

def search_keywords(data, query):
    """Search for keywords containing the query."""
    results = [row for row in data if query.lower() in row.get('search_term', '').lower()]

    print(f"\n🔍 Found {len(results)} results for '{query}':")
    print("-" * 80)

    for i, row in enumerate(results[:20], 1):  # Show first 20 results
        keyword = row.get('search_term', '')
        language = row.get('language', 'unknown')
        print(f"{i}. [{language}] {keyword}")

    if len(results) > 20:
        print(f"\n... and {len(results) - 20} more results")

def filter_by_language(data, lang_code):
    """Show keywords for specific language."""
    results = [row for row in data if row.get('language', '').lower() == lang_code.lower()]

    print(f"\n🌍 Found {len(results)} keywords in language '{lang_code}':")
    print("-" * 80)

    for i, row in enumerate(results[:30], 1):  # Show first 30 results
        keyword = row.get('search_term', '')
        print(f"{i}. {keyword}")

    if len(results) > 30:
        print(f"\n... and {len(results) - 30} more results")

def interactive_mode(data):
    """Interactive search mode."""
    while True:
        try:
            command = input("\n> ").strip()

            if not command:
                continue

            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            elif command.lower() == 'stats':
                analyze_data(data)

            elif command.lower().startswith('search '):
                query = command[7:]
                search_keywords(data, query)

            elif command.lower().startswith('lang '):
                lang_code = command[5:].strip()
                filter_by_language(data, lang_code)

            else:
                print("❌ Unknown command. Use: search <text>, lang <code>, stats, or quit")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break

def main():
    filepath = 'keywords.csv'

    print("🚀 Loading keywords.csv...")
    data = load_csv(filepath)

    if not data:
        sys.exit(1)

    # Show initial analysis
    analyze_data(data)

    # Enter interactive mode
    print("\nEntering interactive mode...")
    interactive_mode(data)

if __name__ == '__main__':
    main()
