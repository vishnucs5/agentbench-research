from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from packages.domain.config import Settings
from pydantic import ValidationError


@pytest.fixture
def monkey_patch_env_missing_demo(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)


def test_demo_mode_defaults_false(monkey_patch_env_missing_demo):
    from packages.domain.config import Settings

    s = Settings(_env_file=None, SECRET_KEY="x" * 32)
    assert s.demo_mode is False


def test_settings_defaults():
    with patch.dict(
        os.environ,
        {
            "SECRET_KEY": "a" * 32,
            "OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)
        assert settings.app_env == "development"
        assert settings.log_level == "DEBUG"
        assert settings.default_model_provider == "ollama"
        assert settings.model_profile == "balanced"


def test_settings_secret_key_validation():
    with patch.dict(
        os.environ,
        {
            "SECRET_KEY": "short",
            "OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        with pytest.raises(ValidationError):
            Settings()


def test_settings_from_env():
    with patch.dict(
        os.environ,
        {
            "SECRET_KEY": "a" * 32,
            "APP_ENV": "production",
            "LOG_LEVEL": "INFO",
            "DEFAULT_MODEL_PROVIDER": "openrouter",
            "MODEL_PROFILE": "fast",
            "OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.app_env == "production"
        assert settings.log_level == "INFO"
        assert settings.default_model_provider == "openrouter"
        assert settings.model_profile == "fast"


def test_settings_is_development():
    with patch.dict(
        os.environ,
        {
            "SECRET_KEY": "a" * 32,
            "APP_ENV": "development",
            "OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.is_development is True
        assert settings.is_production is False


def test_settings_is_production():
    with patch.dict(
        os.environ,
        {
            "SECRET_KEY": "a" * 32,
            "APP_ENV": "production",
            "OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.is_development is False
        assert settings.is_production is True
