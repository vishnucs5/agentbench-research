import os
import sys
from pathlib import Path

# Set test environment variables before any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEFAULT_MODEL_PROVIDER", "mock")
os.environ.setdefault("MODEL_PROFILE", "fast")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


pytest_plugins = ["pytest_asyncio"]
