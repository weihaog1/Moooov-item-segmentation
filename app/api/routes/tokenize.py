"""Tokenization API endpoints."""

import time
import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TokenizeRequest,
    TokenizeResponse,
    BatchTokenizeRequest,
    BatchTokenizeResponse,
)
from app.services.processor import keyword_processor

router = APIRouter(prefix="/api/v1", tags=["tokenization"])


@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize_keyword(request: TokenizeRequest) -> TokenizeResponse:
    """
    Tokenize and tag a single keyword.

    - **keyword**: The product keyword to process
    - **language**: Optional language code (auto-detected if not provided)
    - **use_cache**: Whether to use cached results (default: true)
    - **learn_patterns**: Whether to learn new patterns (default: true)

    Returns tokenized and tagged result with semantic categories.
    """
    try:
        return await keyword_processor.process(
            keyword=request.keyword,
            language=request.language,
            use_cache=request.use_cache,
            learn_patterns=request.learn_patterns,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.post("/tokenize/batch", response_model=BatchTokenizeResponse)
async def tokenize_batch(request: BatchTokenizeRequest) -> BatchTokenizeResponse:
    """
    Batch process multiple keywords.

    - **keywords**: List of keywords to process (max 100)
    - **language**: Optional language code for all keywords
    - **use_cache**: Whether to use cached results
    - **learn_patterns**: Whether to learn new patterns

    Processes keywords concurrently for better performance.
    """
    if len(request.keywords) > 100:
        raise HTTPException(
            status_code=400, detail="Maximum 100 keywords per batch request"
        )

    start_time = time.time()

    # Process all keywords concurrently
    tasks = [
        keyword_processor.process(
            keyword=kw,
            language=request.language,
            use_cache=request.use_cache,
            learn_patterns=request.learn_patterns,
        )
        for kw in request.keywords
    ]

    try:
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000

        return BatchTokenizeResponse(
            results=results,
            total_processed=len(results),
            total_time_ms=round(total_time, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")
