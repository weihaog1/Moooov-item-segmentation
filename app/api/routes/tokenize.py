"""Tokenization API endpoints."""

import time
import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TokenizeRequest,
    TokenizeResponse,
    BatchTokenizeRequest,
    BatchTokenizeResponse,
    AsyncJobResponse,
    AsyncJobResultResponse,
    BatchAsyncRequest,
)
from app.services.processor import keyword_processor
from app.tasks.dictionary_tasks import dictionary_lookup_task
from app.tasks.llm_tasks import llm_process_task
from app.tasks.batch_tasks import batch_process_task, batch_get_results_task

router = APIRouter(prefix="/api/v1", tags=["tokenization"])


@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize_keyword(request: TokenizeRequest) -> TokenizeResponse:
    """
    Tokenize and tag a single keyword.

    - **keyword**: The product keyword to process
    - **language**: Optional language code (auto-detected if not provided)
    - **use_cache**: Whether to use cached results (default: true)
    - **learn_patterns**: Whether to learn new patterns (default: true)
    - **use_spacy**: Whether to use spaCy-based tokenization with learned patterns (default: false)

    Returns tokenized and tagged result with semantic categories.
    """
    try:
        return await keyword_processor.process(
            keyword=request.keyword,
            language=request.language,
            use_cache=request.use_cache,
            learn_patterns=request.learn_patterns,
            use_spacy=request.use_spacy,
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
    - **use_spacy**: Whether to use spaCy-based tokenization with learned patterns

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
            use_spacy=request.use_spacy,
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


@router.post("/tokenize/async", response_model=AsyncJobResponse)
async def tokenize_async(request: TokenizeRequest) -> AsyncJobResponse:
    """
    Submit async tokenization job.

    Returns a job_id that can be used to poll for results.
    Useful for long-running requests or high-volume processing.

    - **keyword**: The product keyword to process
    - **language**: Optional language code (auto-detected if not provided)

    The job will be processed by either dictionary workers (fast) or LLM workers
    depending on system configuration.
    """
    try:
        # Submit to dictionary task queue (fast path)
        task = dictionary_lookup_task.apply_async(
            args=[request.keyword, request.language or "en"]
        )

        return AsyncJobResponse(
            job_id=task.id,
            status="queued",
            message="Job submitted for processing",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit async job: {str(e)}"
        )


@router.get("/tokenize/async/{job_id}", response_model=AsyncJobResultResponse)
async def get_async_result(job_id: str) -> AsyncJobResultResponse:
    """
    Get result of async tokenization job.

    Poll this endpoint with the job_id returned from /tokenize/async
    to check status and retrieve results when ready.

    - **job_id**: The job ID returned from async submission
    """
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app

    try:
        result = AsyncResult(job_id, app=celery_app)

        if result.ready():
            if result.successful():
                return AsyncJobResultResponse(
                    job_id=job_id,
                    status="completed",
                    result=result.get(),
                )
            else:
                return AsyncJobResultResponse(
                    job_id=job_id,
                    status="failed",
                    error=str(result.info),
                )
        else:
            return AsyncJobResultResponse(
                job_id=job_id,
                status="processing",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")


@router.post("/tokenize/batch/async", response_model=AsyncJobResponse)
async def batch_tokenize_async(request: BatchAsyncRequest) -> AsyncJobResponse:
    """
    Submit async batch processing job.

    Process large batches of keywords asynchronously.
    Supports up to 1000 keywords per batch.

    - **keywords**: List of dicts with 'keyword' and 'language' keys
    - **use_llm**: If true, use LLM workers (slower, more accurate);
                   if false, use dictionary workers (faster, less accurate)

    Returns a batch_id that can be used to poll for results.
    """
    try:
        # Submit batch processing task
        task = batch_process_task.apply_async(
            args=[request.keywords, request.use_llm]
        )

        # The task itself returns batch info
        result = task.get(timeout=5)  # Quick wait for batch submission

        return AsyncJobResponse(
            job_id=result.get("batch_id", task.id),
            status="queued",
            message=f"Batch of {result.get('total_tasks', 0)} tasks submitted",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit batch job: {str(e)}"
        )


@router.get("/tokenize/batch/async/{batch_id}", response_model=AsyncJobResultResponse)
async def get_batch_async_result(batch_id: str) -> AsyncJobResultResponse:
    """
    Get results of async batch processing job.

    Poll this endpoint with the batch_id to check progress and
    retrieve results when all tasks are completed.

    - **batch_id**: The batch ID returned from batch async submission
    """
    try:
        # Get batch results
        task = batch_get_results_task.apply_async(args=[batch_id])
        result = task.get(timeout=5)

        status_map = {
            "completed": "completed",
            "processing": "processing",
            "error": "failed",
            "not_found": "failed",
        }

        return AsyncJobResultResponse(
            job_id=batch_id,
            status=status_map.get(result.get("status", "failed"), "failed"),
            result=result.get("results") if result.get("status") == "completed" else None,
            error=result.get("error"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch results: {str(e)}"
        )
