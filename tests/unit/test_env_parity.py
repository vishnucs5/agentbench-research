from __future__ import annotations

from pathlib import Path


def test_env_example_parity() -> None:
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text()
    for key in [
        "SECRET_KEY",
        "REDIS_URL",
        "CACHE_DEFAULT_TTL",
        "CACHE_ENABLED",
        "DEMO_MODE",
        "DEMO_USER_EMAIL",
        "LOCAL_STORAGE_PATH",
        "BM25_INDEX_PATH",
        "MINIO_SECURE",
    ]:
        assert key in text, f"missing {key}"
