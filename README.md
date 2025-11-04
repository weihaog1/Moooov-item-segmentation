# E-Commerce Item Segmentation System

AI-powered keyword segmentation and semantic tagging for multilingual e-commerce product titles.

## Features

- **Multilingual Support**: Chinese, English, Spanish, Japanese, Korean
- **LLM-Powered Processing**: Uses Google Gemini 2.0 Flash for accurate tokenization and tagging
- **8 Semantic Categories**: Brand, Product, Audience, Scenario, Color, Size, Selling Point, Attribute
- **Smart Caching**: Two-tier cache (in-memory + SQLite) reduces API costs
- **Dictionary Learning**: Automatically learns patterns from high-confidence results

## Quick Start

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# Initialize database
python scripts/init_db.py

# Run server
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

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

```bash
# Process single keyword
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"keyword": "Nike Air Max 90 男款黑色跑步鞋"}'

# Batch processing
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["keyword1", "keyword2"]}'
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## License

MIT
