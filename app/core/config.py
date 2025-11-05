"""Application configuration management."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini API
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp", description="Gemini model name"
    )
    gemini_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM temperature for consistency"
    )

    # Database - MySQL
    db_host: str = Field(default="localhost", description="MySQL host")
    db_port: int = Field(default=3306, ge=1, le=65535, description="MySQL port")
    db_user: str = Field(default="apiuser", description="MySQL username")
    db_password: str = Field(default="apipassword", description="MySQL password")
    db_name: str = Field(default="segmentation", description="MySQL database name")

    # Cache settings
    cache_ttl_seconds: int = Field(
        default=86400, ge=0, description="Cache TTL in seconds (24 hours default)"
    )
    max_cache_size: int = Field(
        default=1000, ge=1, description="Max in-memory cache entries"
    )

    # Learning settings
    enable_learning: bool = Field(
        default=True, description="Enable automatic dictionary learning"
    )
    learning_confidence_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Min confidence for learning"
    )
    learning_min_occurrences: int = Field(
        default=3, ge=1, description="Min occurrences before learning pattern"
    )

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )

    # Supported languages
    supported_languages: list[str] = Field(
        default=["zh", "en", "es", "ja", "ko"], description="Supported language codes"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
