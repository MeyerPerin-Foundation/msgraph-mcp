"""Tests for configuration module."""

import os
from unittest import mock

from msgraph_mcp.config import is_user_allowed


def test_default_allowed_user():
    assert is_user_allowed("lucas.augusto.meyer@outlook.com")


def test_case_insensitive():
    assert is_user_allowed("Lucas.Augusto.Meyer@Outlook.com")


def test_disallowed_user():
    assert not is_user_allowed("someone.else@outlook.com")


def test_env_override():
    with mock.patch.dict(os.environ, {"MSGRAPH_MCP_ALLOWED_USERS": "alice@outlook.com, bob@outlook.com"}):
        # Re-import to pick up the env var
        import importlib
        import msgraph_mcp.config as cfg
        importlib.reload(cfg)

        assert cfg.is_user_allowed("alice@outlook.com")
        assert cfg.is_user_allowed("bob@outlook.com")
        assert not cfg.is_user_allowed("lucas.augusto.meyer@outlook.com")

        # Restore default
        importlib.reload(cfg)
