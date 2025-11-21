"""Batch processing tasks for handling multiple keywords."""

from typing import List, Dict, Any
from celery import group
from app.tasks.celery_app import celery_app
from app.tasks.dictionary_tasks import dictionary_lookup_task
from app.tasks.llm_tasks import llm_process_task


@celery_app.task(name="tasks.batch_process", bind=True)
def batch_process_task(
    self, keywords: List[Dict[str, str]], use_llm: bool = False
) -> Dict[str, Any]:
    """
    Process a batch of keywords in streaming fashion.

    Creates a group of tasks (dictionary or LLM) and executes them in parallel.

    Args:
        keywords: List of dicts with 'keyword' and 'language' keys
        use_llm: If True, use LLM processing; otherwise use dictionary-only

    Returns:
        Dict with batch_id, total_tasks, and status
    """
    # Validate input
    if not keywords:
        return {
            "error": "No keywords provided",
            "status": "failed",
        }

    if len(keywords) > 1000:
        return {
            "error": "Batch size exceeds maximum of 1000 keywords",
            "status": "failed",
        }

    # Create task group
    if use_llm:
        # Use LLM worker pool
        job_group = group(
            llm_process_task.s(kw["keyword"], kw["language"]) for kw in keywords
        )
    else:
        # Use dictionary worker pool (faster)
        job_group = group(
            dictionary_lookup_task.s(kw["keyword"], kw["language"]) for kw in keywords
        )

    # Execute tasks in parallel (don't wait - return immediately)
    result = job_group.apply_async()

    # Store group result for later retrieval
    # Save the result using the result backend
    result.save()

    # Return immediately with the group ID
    return {
        "batch_id": result.id,
        "total": len(keywords),
        "status": "processing",
        "processing_method": "llm" if use_llm else "dictionary",
    }


@celery_app.task(name="tasks.batch_get_results", bind=True)
def batch_get_results_task(self, batch_id: str) -> Dict[str, Any]:
    """
    Get results from a batch processing job.

    Args:
        batch_id: The batch job ID returned from batch_process_task

    Returns:
        Dict with status and results (if ready)
    """
    from celery.result import GroupResult

    result = GroupResult.restore(batch_id, app=celery_app)

    if result is None:
        return {
            "error": "Batch not found",
            "status": "not_found",
        }

    if result.ready():
        # All tasks completed
        try:
            results = result.get(timeout=1.0)
            return {
                "status": "completed",
                "total": len(results),
                "results": results,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    elif result.failed():
        # Some tasks failed
        return {
            "status": "failed",
            "completed": result.completed_count(),
            "total": len(result),
        }
    else:
        # Still processing
        return {
            "status": "processing",
            "completed": result.completed_count(),
            "total": len(result),
        }
