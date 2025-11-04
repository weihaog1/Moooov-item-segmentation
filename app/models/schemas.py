"""Pydantic schemas for API requests and responses."""

from typing import Literal
from pydantic import BaseModel, Field


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


class BatchTokenizeRequest(BaseModel):
    """Request to batch process multiple keywords."""

    keywords: list[str] = Field(
        ..., min_length=1, max_length=100, description="Keywords to process"
    )
    language: str | None = Field(None, description="Language code for all keywords")
    use_cache: bool = Field(default=True, description="Whether to use cache")
    learn_patterns: bool = Field(default=True, description="Whether to learn patterns")


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


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(..., description="System status")
    database: bool = Field(..., description="Database connection status")
    gemini_api: bool = Field(..., description="Gemini API status")
    details: dict = Field(default_factory=dict, description="Additional details")
