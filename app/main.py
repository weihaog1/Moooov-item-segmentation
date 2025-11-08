"""Main FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import tokenize, health
from app.core.config import settings
from app.services.spacy_processor import spacy_processor

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="E-Commerce Item Segmentation API",
    description="AI-powered keyword tokenization and semantic tagging for multilingual e-commerce products",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tokenize.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting up application...")

    # Initialize spaCy tokenizer with learned patterns
    try:
        logger.info("Initializing spaCy tokenizer with learned patterns...")
        await spacy_processor.initialize()
        logger.info("spaCy tokenizer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize spaCy tokenizer: {e}")
        logger.warning("spaCy will not be available, falling back to simple tokenization")
        # Continue anyway - will fall back to simple tokenization or LLM


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "E-Commerce Item Segmentation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "supported_languages": settings.supported_languages,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
