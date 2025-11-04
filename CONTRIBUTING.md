# Contributing Guide

## Development Setup

```bash
# Clone and install
git clone https://github.com/weihaog1/Moooov-item-gegmentation.git
cd Moooov-item-gegmentation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your GEMINI_API_KEY

# Initialize database
python scripts/init_db.py
```

## Code Style

We follow Python best practices:

- **Formatting**: Use `black` for code formatting
- **Type Hints**: Always use type hints for function parameters and returns
- **Docstrings**: Use Google-style docstrings for all modules, classes, and functions
- **Line Length**: Max 88 characters (black default)

```bash
# Format code
black app/ tests/

# Check types
mypy app/
```

## Testing

All new features must include tests:

```bash
# Run tests
pytest

# Run with coverage (must maintain >80% coverage)
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::test_health_endpoint -v
```

## Commit Messages

Follow conventional commit format:

```
<type>: <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring
- `chore`: Build/config changes

Examples:
```
feat: add Spanish language support
fix: handle empty keyword edge case
docs: update API examples in README
test: add integration tests for batch processing
```

## Pull Request Process

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make changes with clear commit messages
3. Add/update tests
4. Ensure all tests pass: `pytest`
5. Update documentation if needed
6. Push and create pull request

## Project Structure

```
app/
├── core/          # Configuration and settings
├── db/            # Database layer and schema
├── services/      # Business logic services
├── api/           # FastAPI routes and endpoints
├── models/        # Pydantic schemas
└── utils/         # Helper utilities

tests/             # Test suite
scripts/           # Utility scripts
data/              # Database files (not in git)
```

## Adding New Features

### Adding a New Tag Category

1. Update `TagType` in `app/models/schemas.py`
2. Add table in `app/db/database.py`
3. Add lookup method in `app/db/manager.py`
4. Update LLM prompt in `app/services/llm_processor.py`
5. Add tests

### Adding a New Language

1. Add language code to `supported_languages` in `app/core/config.py`
2. Update detection logic in `app/utils/language_detector.py`
3. Add language-specific examples in `app/services/llm_processor.py`
4. Add tests

## Performance Considerations

- Use async/await throughout
- Cache aggressively (check cache before LLM calls)
- Batch process when possible
- Monitor LLM token usage
- Database queries should use indexes

## Questions?

Open an issue on GitHub for questions or discussions.
