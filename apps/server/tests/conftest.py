"""Pytest configuration."""

import pytest


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Mock settings for all tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
