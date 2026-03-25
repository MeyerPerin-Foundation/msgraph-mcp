"""Shared test fixtures for msgraph-mcp tests."""

import os
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def mock_oauth_env():
    """Set dummy OAuth env vars for all tests."""
    with mock.patch.dict(os.environ, {
        "MSGRAPH_CLIENT_ID": "test-client-id",
        "MSGRAPH_CLIENT_SECRET": "test-client-secret",
        "MSGRAPH_REDIRECT_URI": "http://localhost:8000/auth/microsoft/callback",
        "MSGRAPH_SERVER_URL": "http://localhost:8000",
    }):
        yield
