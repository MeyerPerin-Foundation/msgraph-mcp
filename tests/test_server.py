"""Tests for server auth configuration."""


def test_server_sets_default_client_registration_scope():
    """Dynamic client registration should default clients to the MCP tool scope."""
    import importlib

    import msgraph_mcp.server as server_module
    from msgraph_mcp.config import MCP_REQUIRED_SCOPES

    server = importlib.reload(server_module)
    auth_settings = server.mcp.settings.auth

    assert auth_settings is not None
    assert auth_settings.required_scopes == MCP_REQUIRED_SCOPES
    assert auth_settings.client_registration_options is not None
    assert auth_settings.client_registration_options.valid_scopes == MCP_REQUIRED_SCOPES
    assert auth_settings.client_registration_options.default_scopes == MCP_REQUIRED_SCOPES
