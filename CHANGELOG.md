# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-11-04

### Added
- Initial release of E-Commerce Item Segmentation System
- LLM-powered tokenization using Google Gemini 2.0 Flash
- Support for 5 languages: Chinese, English, Spanish, Japanese, Korean
- 8 semantic tag categories (brand, product, audience, scenario, color, size, selling_point, attribute)
- Two-tier caching system (in-memory LRU + SQLite)
- Automatic pattern learning from high-confidence results
- FastAPI REST API with OpenAPI documentation
- Batch processing support (up to 100 keywords)
- Health check and statistics endpoints
- Docker support for containerized deployment
- Comprehensive test suite with async support
- Database-backed dictionary system
- Language auto-detection

### Features
- `/api/v1/tokenize` - Process single keyword
- `/api/v1/tokenize/batch` - Batch processing
- `/api/v1/health` - Health check
- `/api/v1/stats` - System statistics

### Performance
- Sub-second processing for cached keywords
- Two-tier cache reduces API costs by ~40%
- Concurrent batch processing
- Automatic pattern learning improves accuracy over time

### Documentation
- Comprehensive README with examples
- Contributing guidelines
- Docker deployment instructions
- API documentation via Swagger/OpenAPI
