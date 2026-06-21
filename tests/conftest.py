"""Shared pytest fixtures for blackbull-demo tests."""

import pytest
from blackbull.testing import TestClient


@pytest.fixture
def app():
    """Create a BlackBull application instance for testing."""
    from blackbull_demo.app import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Create a synchronous TestClient bound to the application."""
    with TestClient(app) as c:
        yield c
