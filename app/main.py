"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import tokenize, health
from app.core.config import settings

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
