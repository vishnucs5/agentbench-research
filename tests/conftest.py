import os
import sys
from pathlib import Path

import pytest

# Set test environment variables before any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEFAULT_MODEL_PROVIDER", "mock")
os.environ.setdefault("MODEL_PROFILE", "fast")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("QDRANT_URL", "memory://")

sys.path.insert(0, str(Path(__file__).parent.parent))

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from packages.domain.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
