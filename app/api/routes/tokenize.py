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

    - **keywords**: List of keywords to process (max 500)
    - **language**: Optional language code for all keywords
    - **use_cache**: Whether to use cached results
    - **learn_patterns**: Whether to learn new patterns
    - **use_spacy**: Whether to use spaCy-based tokenization with learned patterns

    Processes keywords concurrently for better performance.
    """
    if len(request.keywords) > 500:
        raise HTTPException(
            status_code=400, detail="Maximum 500 keywords per batch request"
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

    Processing behavior is controlled by USE_LLM_FIRST environment variable:
    - True (default): Always use LLM for accurate results, learn to dictionary
    - False: Use dictionary first, fallback to LLM only if unknowns found
    """
    from app.core.config import settings

    try:
        # Choose task based on USE_LLM_FIRST toggle
        if settings.use_llm_first:
            # LLM-first mode: Always use LLM (best for early stage)
            task = llm_process_task.apply_async(
                args=[request.keyword, request.language or "en"]
            )
        else:
            # Dictionary-first mode: Fast path with LLM fallback
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
        # Convert KeywordItem objects to dicts for Celery
        keywords_list = [{"keyword": kw.keyword, "language": kw.language} for kw in request.keywords]

        # Submit batch processing task
        task = batch_process_task.apply_async(
            args=[keywords_list, request.use_llm],
            queue="batch"
        )

        return AsyncJobResponse(
            job_id=task.id,
            status="queued",
            message=f"Batch of {len(keywords_list)} tasks submitted",
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
    from celery.result import GroupResult, AsyncResult
    from app.tasks.celery_app import celery_app

    try:
        # Check batch_process_task status
        task_result = AsyncResult(batch_id, app=celery_app)

        if task_result.state == "SUCCESS":
            # Get the group ID without blocking
            try:
                batch_data = task_result.get(timeout=0.5)
                actual_batch_id = batch_data.get("batch_id")

                if not actual_batch_id:
                    return AsyncJobResultResponse(
                        job_id=batch_id,
                        status="failed",
                        result=None,
                        error="No group ID found in batch task result",
                    )

                # Check the group result
                group_result = GroupResult.restore(actual_batch_id, app=celery_app)

                if not group_result:
                    return AsyncJobResultResponse(
                        job_id=batch_id,
                        status="failed",
                        result=None,
                        error="Group result not found",
                    )

                if group_result.ready():
                    # All tasks completed
                    try:
                        results = group_result.get(timeout=1.0)
                        return AsyncJobResultResponse(
                            job_id=batch_id,
                            status="completed",
                            result={"results": results, "total": len(results)},
                            error=None,
                        )
                    except Exception as e:
                        return AsyncJobResultResponse(
                            job_id=batch_id,
                            status="failed",
                            result=None,
                            error=f"Error getting results: {str(e)}",
                        )
                else:
                    # Still processing individual tasks
                    completed = group_result.completed_count() if hasattr(group_result, 'completed_count') else 0
                    total = len(group_result) if hasattr(group_result, '__len__') else 0
                    return AsyncJobResultResponse(
                        job_id=batch_id,
                        status="processing",
                        result={"completed": completed, "total": total},
                        error=None,
                    )
            except Exception as e:
                return AsyncJobResultResponse(
                    job_id=batch_id,
                    status="failed",
                    result=None,
                    error=f"Error retrieving batch data: {str(e)}",
                )
        elif task_result.state == "FAILURE":
            return AsyncJobResultResponse(
                job_id=batch_id,
                status="failed",
                result=None,
                error=str(task_result.info),
            )
        else:
            # Still queued or processing the batch task itself
            return AsyncJobResultResponse(
                job_id=batch_id,
                status="processing",
                result=None,
                error=None,
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch results: {str(e)}"
        )
