"""Pydantic schemas for API requests and responses."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


# Tag types
TagType = Literal[
    "brand_term",
    "product_term",
    "audience_term",
    "scenario_term",
    "color_term",
    "size_term",
    "selling_point_term",
    "attribute_term",
]


class TokenTag(BaseModel):
    """Represents a tagged token."""

    token: str = Field(..., description="The token text")
    tags: list[TagType] = Field(
        default_factory=list, description="Semantic tags for this token"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )


class TokenizeRequest(BaseModel):
    """Request to tokenize and tag a keyword."""

    keyword: str = Field(..., min_length=1, description="The keyword to process")
    language: str | None = Field(
        None, description="Language code (auto-detect if not provided)"
    )
    use_cache: bool = Field(default=True, description="Whether to use cache")
    learn_patterns: bool = Field(
        default=True, description="Whether to learn new patterns"
    )
    use_spacy: bool = Field(
        default=False, description="Whether to use spaCy-based tokenization with learned patterns (skip LLM if all tokens match)"
    )


class TokenizeResponse(BaseModel):
    """Response from tokenization."""

    original_keyword: str = Field(..., description="Original input keyword")
    language: str = Field(..., description="Detected/specified language")
    tokens: list[str] = Field(..., description="Extracted tokens")
    tagged_tokens: list[TokenTag] = Field(..., description="Tokens with tags")
    tag_summary: dict[str, list[str]] = Field(
        ..., description="Tokens grouped by tag type"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cache_hit: bool = Field(..., description="Whether result was from cache")
    pattern_matched: bool = Field(
        default=False, description="Whether result was from pattern matching (skipped LLM)"
    )


class BatchTokenizeRequest(BaseModel):
    """Request to batch process multiple keywords."""

    keywords: list[str] = Field(
        ..., min_length=1, max_length=500, description="Keywords to process (max 500)"
    )
    language: str | None = Field(None, description="Language code for all keywords")
    use_cache: bool = Field(default=True, description="Whether to use cache")
    learn_patterns: bool = Field(default=True, description="Whether to learn patterns")
    use_spacy: bool = Field(
        default=False, description="Whether to use spaCy-based tokenization with learned patterns"
    )


class BatchTokenizeResponse(BaseModel):
    """Response from batch tokenization."""

    results: list[TokenizeResponse] = Field(..., description="Results for each keyword")
    total_processed: int = Field(..., description="Total keywords processed")
    total_time_ms: float = Field(..., description="Total processing time")


class DictionaryEntry(BaseModel):
    """Generic dictionary entry."""

    term: str = Field(..., description="The term/pattern")
    language: str = Field(..., description="Language code")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Confidence")
    source: Literal["seed", "ai_learned"] = Field(
        default="seed", description="Entry source"
    )


class AsyncJobResponse(BaseModel):
    """Response for async job submission."""

    job_id: str = Field(..., description="Job ID for polling results")
    status: Literal["queued", "processing", "completed", "failed"] = Field(
        ..., description="Job status"
    )
    message: str = Field(default="", description="Optional status message")


class AsyncJobStatusRequest(BaseModel):
    """Request to check async job status."""

    job_id: str = Field(..., description="Job ID to check")


class AsyncJobResultResponse(BaseModel):
    """Response with async job results."""

    job_id: str = Field(..., description="Job ID")
    status: Literal["queued", "processing", "completed", "failed"] = Field(
        ..., description="Job status"
    )
    result: dict | None = Field(None, description="Job result (if completed)")
    error: str | None = Field(None, description="Error message (if failed)")


class KeywordItem(BaseModel):
    """Single keyword item for batch processing."""
    keyword: str = Field(..., description="The keyword to process")
    language: str = Field(default="en", description="Language code")


class BatchAsyncRequest(BaseModel):
    """Request for async batch processing."""

    keywords: list[KeywordItem] = Field(
        ...,
        description="List of keywords to process",
    )
    use_llm: bool = Field(
        default=False, description="Use LLM processing (slower but more accurate)"
    )

    @field_validator('keywords')
    @classmethod
    def validate_keywords_length(cls, v):
        if len(v) < 1:
            raise ValueError('keywords list must contain at least 1 item')
        if len(v) > 1000:
            raise ValueError('keywords list cannot exceed 1000 items')
        return v


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(..., description="System status")
    database: bool = Field(..., description="Database connection status")
    deepseek_api: bool = Field(..., description="DeepSeek API status")
    details: dict = Field(default_factory=dict, description="Additional details")
