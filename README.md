# E-Commerce Item Segmentation System

AI-powered keyword segmentation and semantic tagging for multilingual e-commerce product titles.

## Features

- **Multilingual Support**: Chinese, English, Spanish, Japanese, Korean
- **LLM-Powered Processing**: Uses Google Gemini 2.0 Flash for accurate tokenization and tagging
- **8 Semantic Categories**: Brand, Product, Audience, Scenario, Color, Size, Selling Point, Attribute
- **Smart Caching**: Two-tier cache (in-memory + SQLite) reduces API costs
- **Dictionary Learning**: Automatically learns patterns from high-confidence results

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/weihaog1/Moooov-item-gegmentation.git
cd Moooov-item-gegmentation

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Initialize database
python scripts/init_db.py

# Run server
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

### Docker Deployment

```bash
# Copy environment file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Project Structure

```
app/
├── core/           # Configuration and logging
├── db/             # Database layer
├── services/       # Business logic (LLM, caching, learning)
├── api/            # FastAPI routes
├── models/         # Pydantic schemas
└── utils/          # Helper functions
```

## API Examples

### Process Single Keyword

```bash
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"keyword": "Nike Air Max 90 black running shoes"}'
```

Response:
```json
{
  "original_keyword": "Nike Air Max 90 black running shoes",
  "language": "en",
  "tokens": ["Nike Air Max 90", "black", "running", "shoes"],
  "tagged_tokens": [
    {"token": "Nike Air Max 90", "tags": ["brand_term", "product_term"], "confidence": 0.95},
    {"token": "black", "tags": ["color_term"], "confidence": 0.95},
    {"token": "running", "tags": ["scenario_term"], "confidence": 0.95},
    {"token": "shoes", "tags": ["product_term"], "confidence": 0.95}
  ],
  "tag_summary": {
    "brand_term": ["Nike Air Max 90"],
    "product_term": ["Nike Air Max 90", "shoes"],
    "color_term": ["black"],
    "scenario_term": ["running"]
  },
  "processing_time_ms": 234.5,
  "cache_hit": false
}
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["Apple iPhone 15 Pro", "Nike Air Max 90"]}'
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### System Statistics

```bash
curl http://localhost:8000/api/v1/stats
```

## Semantic Tag Categories

The system classifies tokens into 8 semantic categories:

| Tag Type | Description | Examples |
|----------|-------------|----------|
| `brand_term` | Brand names | Apple, Nike, 华为 |
| `product_term` | Product categories | shoes, laptop, 手机 |
| `audience_term` | Target demographic | men's, kids, 学生 |
| `scenario_term` | Usage context | running, office, 运动 |
| `color_term` | Colors | black, red, 黑色 |
| `size_term` | Sizes/dimensions | 10.5, 256GB, XL |
| `selling_point_term` | Product features | waterproof, wireless, 防水 |
| `attribute_term` | Technical specs | memory, battery, 内存 |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

## Architecture

The system uses an LLM-first architecture:

1. **Language Detection** - Auto-detects language (zh/en/es/ja/ko)
2. **LLM Processing** - Gemini 2.0 Flash performs tokenization and tagging in one call
3. **Dictionary Enrichment** - Enhances results with pre-defined dictionaries
4. **Pattern Learning** - Automatically learns from high-confidence results (≥0.85)
5. **Caching** - Two-tier cache (memory + SQLite) reduces API costs

## Configuration

Key environment variables in `.env`:

```bash
GEMINI_API_KEY=your_key                  # Required
CACHE_TTL_SECONDS=86400                   # Cache lifetime (24 hours)
MAX_CACHE_SIZE=1000                       # In-memory cache entries
ENABLE_LEARNING=true                      # Auto-learn patterns
LEARNING_CONFIDENCE_THRESHOLD=0.85        # Min confidence for learning
LEARNING_MIN_OCCURRENCES=3                # Min occurrences before pattern is learned
```

## License

MIT
