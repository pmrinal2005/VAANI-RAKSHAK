# ==============================================================================
# Shared test fixtures and configuration
# ==============================================================================

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def app():
    """Return a fresh application instance for testing."""
    # Clear cached settings so tests can use env overrides
    get_settings.cache_clear()
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """Return a synchronous TestClient for route-level tests."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset the Settings singleton cache between tests that override env vars."""
    yield
    get_settings.cache_clear()
