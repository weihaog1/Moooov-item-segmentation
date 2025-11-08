# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Initialization

**Local Development (requires local MySQL):**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up MySQL database and user
mysql -u root -p
# CREATE DATABASE segmentation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE USER 'apiuser'@'localhost' IDENTIFIED BY 'apipassword';
# GRANT ALL PRIVILEGES ON segmentation.* TO 'apiuser'@'localhost';
# FLUSH PRIVILEGES; EXIT;

# Configure environment
cp .env.example .env
# Edit .env with your DEEPSEEK_API_KEY and MySQL credentials

# Initialize database tables
python scripts/init_db.py

# Run development server with hot reload
uvicorn app.main:app --reload
```

**Docker Development (recommended - includes MySQL):**
```bash
# Start both MySQL and API containers
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop containers
docker-compose down
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_function_name -v
```

### Docker
```bash
# Build and run containers (MySQL + API)
docker-compose up -d

# View API logs
docker-compose logs -f api

# View MySQL logs
docker-compose logs -f mysql

# Stop containers (keeps data)
docker-compose down

# Stop containers and remove volumes (deletes data)
docker-compose down -v
```

## Architecture Overview

### LLM-First Processing Pipeline

The system uses a **two-phase processing approach**:

1. **LLM Phase** (`app/services/llm_processor.py`): DeepSeek API performs tokenization and initial tagging
   - Uses the OpenAI SDK (`openai>=1.0.0`) with DeepSeek's OpenAI-compatible API
   - Client-based API: `AsyncOpenAI()` with async calls via `client.chat.completions.create()`
   - Base URL: `https://api.deepseek.com`
   - Uses carefully crafted prompts with language-specific examples
   - Critical rule: Preserves multi-word entities (e.g., "iPhone 15 Pro" stays together)
   - Returns structured JSON with tokens, tags, and confidence scores (`response_format={"type": "json_object"}`)

2. **Enrichment Phase** (`app/services/processor.py`): Results are enhanced with:
   - Dictionary lookups (brands, products, colors, etc.)
   - Learned patterns from previous high-confidence results
   - Confidence score updates based on multiple sources

### Key Components

**`app/services/processor.py`** - Main orchestrator
- Coordinates the entire processing pipeline
- Calls LLM processor for initial tokenization
- Enriches results with dictionary lookups (8 semantic categories)
- Triggers pattern learning for high-confidence results (≥0.85)
- Builds tag summaries and response objects

**`app/services/cache.py`** - Two-tier caching
- **Memory tier**: OrderedDict-based LRU cache (default: 1000 entries)
- **MySQL tier**: Persistent cache with hit tracking and TTL
- Cache key: SHA256 hash of `lowercase(keyword)|language`
- Memory cache is checked first, MySQL is fallback
- Uses connection pooling for optimal MySQL performance

**`app/db/manager.py`** - Dictionary and pattern management
- Manages 7 predefined dictionaries (brands, products, colors, audience, scenario, selling_point, attribute)
- Handles learned pattern storage in `tag_mappings` table
- Pattern learning requires: confidence ≥0.85, min 3 occurrences (configurable)
- All lookups are case-insensitive (normalized to lowercase)

**`app/core/config.py`** - Configuration via Pydantic
- Loads from `.env` file
- Key settings: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Learning settings: `ENABLE_LEARNING`, `CACHE_TTL_SECONDS`
- Uses `pydantic_settings` for validation and type safety

**`app/db/database.py`** - MySQL connection management
- Global connection pool (`aiomysql.Pool`) for efficient connections
- Pool size: min=1, max=10 connections
- All tables use InnoDB engine with utf8mb4 charset for full Unicode support
- Automatic connection pooling prevents connection exhaustion

### Database Schema

MySQL database with these key tables:
- `processing_cache`: Stores processed results with hit counts
- `tag_mappings`: Learned patterns (term → tag mappings with occurrence counts)
- `brands`, `product_terms`, `color_terms`, etc.: Predefined dictionaries

All dictionary tables have:
- `normalized_term` VARCHAR(255) (lowercase, indexed)
- `confidence` FLOAT
- `language` VARCHAR(10)
- Unique constraints on (normalized_term, language)
- InnoDB engine with utf8mb4_unicode_ci collation

### The 8 Semantic Tag Categories

Tokens can have **multiple tags**. The system recognizes:
- `brand_term`: Apple, Nike, 华为
- `product_term`: shoes, laptop, 手机
- `audience_term`: men's, kids, 学生
- `scenario_term`: running, office, 运动
- `color_term`: black, red, 黑色
- `size_term`: 10.5, 256GB, XL
- `selling_point_term`: waterproof, wireless, 防水
- `attribute_term`: memory, battery, 内存

## Important Development Notes

### Adding New Features

- The system is designed to work **without modification** of the LLM prompt for most cases
- To add new dictionary categories:
  1. Add CREATE TABLE statement in `app/db/database.py`
  2. Add lookup method in `app/db/manager.py`
  3. Add enrichment logic in `app/services/processor.py`
- Cache invalidation: Cache entries expire based on `CACHE_TTL_SECONDS` (default: 24 hours)
- MySQL connection pool is automatically managed - no manual connection handling needed

### Testing Considerations

- Tests use temporary MySQL databases via `conftest.py` fixtures
- Mock DeepSeek API calls in tests (API key required for integration tests)
- The `test_db` fixture automatically creates and cleans up test databases
- For local testing without Docker, ensure MySQL is running on localhost:3306
- Connection pool is properly closed in test teardown

### Configuration Priority

Settings are loaded in this order (highest priority first):
1. Environment variables
2. `.env` file
3. Default values in `config.py`

### Pattern Learning Mechanism

When `ENABLE_LEARNING=true`:
1. After processing, high-confidence tokens (≥0.85) are stored in `tag_mappings`
2. Each occurrence increments `occurrence_count`
3. Only patterns with `occurrence_count ≥ LEARNING_MIN_OCCURRENCES` are used for enrichment
4. This creates a feedback loop that improves accuracy over time

### Multilingual Support

Currently supports: Chinese (zh), English (en), Spanish (es), Indonesian (id), Portuguese (pt), French (fr), Japanese (ja), Russian (ru), German (de), Korean (ko)
- Language detection is automatic if not specified using the langdetect library
- Language-specific examples are embedded in LLM prompts for zh and en
- Dictionary lookups are language-scoped (same term can have different tags per language)
- All languages use the same LLM model without language-specific prompt modifications

### MySQL Connection Details

**Connection Pooling:**
- Uses `aiomysql` for async MySQL operations
- Global connection pool created on first use
- Pool configuration: minsize=1, maxsize=10
- Connections automatically recycled

**Query Patterns:**
- All queries use parameterized statements (`%s` placeholders) to prevent SQL injection
- Dictionary lookups: Simple SELECT with indexed columns for fast retrieval
- Cache operations: INSERT ON DUPLICATE KEY UPDATE for upsert behavior
- Learned patterns: GREATEST() function for confidence updates

**Docker MySQL Setup:**
- MySQL 8.0 container with health checks
- API container waits for MySQL to be healthy before starting
- Persistent volume `mysql_data` stores database files
- utf8mb4 charset for full emoji and multilingual support

## Git Commit Guidelines

### Commit Message Format

All commit messages should follow this format:

```
<type>: <subject>

[optional body]
```

**Type must be one of:**
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, missing semicolons, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding or updating tests
- **chore**: Changes to build process, dependencies, or auxiliary tools

**Subject line:**
- Use imperative mood ("add feature" not "added feature")
- Don't capitalize first letter
- No period at the end
- Limit to 72 characters
- Be descriptive in 1-2 sentences

**Examples:**
```
feat: migrate from Gemini API to DeepSeek API for better cost efficiency

fix: correct cache hit tracking to show accurate processing times

docs: update installation guide with Docker setup instructions

chore: upgrade FastAPI to v0.109.0 for security patches
```
