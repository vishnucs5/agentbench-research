from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    secret_key: str = Field(..., min_length=32)
    access_token_expire_minutes: int = 30

    # Database
    postgres_db: str = "agentbench"
    postgres_user: str = "agentbench"
    postgres_password: str = "agentbench"
    database_url: str = "postgresql+asyncpg://agentbench:agentbench@localhost:5432/agentbench"

    # Vector Store
    qdrant_url: str = "http://localhost:6333"

    # Cache settings
    redis_url: str = "redis://localhost:6379/0"
    cache_default_ttl: int = 30  # seconds
    cache_enabled: bool = True

    # Object Storage
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "papers"
    minio_secure: bool = False

    # LLM Providers
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3-coder:30b"

    default_model_provider: Literal["openrouter", "ollama", "mock"] = "ollama"
    model_profile: Literal["balanced", "fast", "local"] = "balanced"

    # Ingestion
    max_file_size_mb: int = 100
    allowed_mime_types: list[str] = ["application/pdf"]
    parser_version: str = "1.0.0"

    # Retrieval
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_top_k: int = 10
    bm25_weight: float = 0.5
    semantic_weight: float = 0.5

    # Agent Budgets
    max_papers_per_run: int = 10
    max_tool_calls_per_run: int = 40
    run_deadline_seconds: int = 180
    token_budget_per_run: int = 100000

    # Security
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Demo mode (passwordless local use; NEVER active in production)
    demo_mode: bool = False  # was True; NEVER active in production
    demo_user_email: str = "demo@test.com"

    # Local fallbacks (used when MinIO/Qdrant are unreachable)
    local_storage_path: str = "data/papers"
    bm25_index_path: str = "data/bm25_index.pkl"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "agentbench-research"
    enable_tracing: bool = True

    # Evaluation
    benchmark_version: str = "1.0.0"
    gold_set_path: str = "data/benchmark/gold.json"

    # Plagiarism Detection
    plagiarism_api_key: str | None = None
    plagiarism_api_url: str = "https://api.plagiarismdetector.com/v1"
    plagiarism_max_upload_size_mb: int = 10
    plagiarism_allowed_mime_types: list[str] = [
        "text/plain",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    plagiarism_similarity_threshold: float = 0.3
    plagiarism_store_submissions: bool = False
    plagiarism_rate_limit_per_minute: int = 10
    plagiarism_rate_limit_per_hour: int = 100

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
