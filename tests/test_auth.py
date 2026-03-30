"""Tests for the MicrosoftOAuthProvider."""

import time

import pytest
from pydantic import AnyUrl

from mcp.server.auth.provider import AuthorizationCode, AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from msgraph_mcp.config import MCP_REQUIRED_SCOPES


def _make_provider():
    """Create a fresh provider with reloaded config."""
    import importlib
    import msgraph_mcp.config as cfg
    importlib.reload(cfg)
    from msgraph_mcp.auth import MicrosoftOAuthProvider
    return MicrosoftOAuthProvider()


def _make_provider_with_store(store=None):
    """Create a fresh provider with reloaded config and optional store."""
    import importlib
    import msgraph_mcp.config as cfg
    importlib.reload(cfg)
    from msgraph_mcp.auth import MicrosoftOAuthProvider
    return MicrosoftOAuthProvider(store=store)


def _make_client(client_id: str = "test-client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_name="Test Client",
        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
    )


@pytest.mark.asyncio
async def test_register_and_get_client():
    provider = _make_provider()
    client = _make_client()
    await provider.register_client(client)
    result = await provider.get_client("test-client")
    assert result is not None
    assert result.client_id == "test-client"


@pytest.mark.asyncio
async def test_get_client_not_found():
    provider = _make_provider()
    result = await provider.get_client("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_authorize_returns_microsoft_url():
    provider = _make_provider()
    client = _make_client()
    params = AuthorizationParams(
        state="csrf-state",
        scopes=["mcp:tools"],
        code_challenge="test-challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    url = await provider.authorize(client, params)
    assert "login.microsoftonline.com" in url
    assert "consumers" in url
    assert len(provider.pending_flows) == 1


@pytest.mark.asyncio
async def test_authorize_stores_flow_context():
    provider = _make_provider()
    client = _make_client()
    params = AuthorizationParams(
        state="csrf-state",
        scopes=["mcp:tools"],
        code_challenge="test-challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    await provider.authorize(client, params)
    flow = list(provider.pending_flows.values())[0]
    assert flow["mcp_state"] == "csrf-state"
    assert flow["mcp_code_challenge"] == "test-challenge"
    assert flow["client_id"] == "test-client"
    assert flow["mcp_scopes"] == MCP_REQUIRED_SCOPES


@pytest.mark.asyncio
async def test_authorize_defaults_scope_when_not_requested():
    provider = _make_provider()
    client = _make_client()
    params = AuthorizationParams(
        state="csrf-state",
        scopes=None,
        code_challenge="test-challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    await provider.authorize(client, params)
    flow = list(provider.pending_flows.values())[0]
    assert flow["mcp_scopes"] == MCP_REQUIRED_SCOPES


@pytest.mark.asyncio
async def test_load_authorization_code_found():
    provider = _make_provider()
    code_obj = AuthorizationCode(
        code="test-code",
        scopes=["mcp:tools"],
        expires_at=time.time() + 300,
        client_id="test-client",
        code_challenge="challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    provider.auth_codes["test-code"] = (code_obj, "user@outlook.com")
    client = _make_client()
    result = await provider.load_authorization_code(client, "test-code")
    assert result is not None
    assert result.code == "test-code"


@pytest.mark.asyncio
async def test_load_authorization_code_expired():
    provider = _make_provider()
    code_obj = AuthorizationCode(
        code="test-code",
        scopes=["mcp:tools"],
        expires_at=time.time() - 10,  # expired
        client_id="test-client",
        code_challenge="challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    provider.auth_codes["test-code"] = (code_obj, "user@outlook.com")
    client = _make_client()
    result = await provider.load_authorization_code(client, "test-code")
    assert result is None


@pytest.mark.asyncio
async def test_exchange_authorization_code_issues_tokens():
    provider = _make_provider()
    code_obj = AuthorizationCode(
        code="test-code",
        scopes=["mcp:tools"],
        expires_at=time.time() + 300,
        client_id="test-client",
        code_challenge="challenge",
        redirect_uri=AnyUrl("http://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )
    provider.auth_codes["test-code"] = (code_obj, "user@outlook.com")
    client = _make_client()
    token = await provider.exchange_authorization_code(client, code_obj)
    assert token.access_token
    assert token.refresh_token
    assert token.token_type.lower() == "bearer"
    assert token.scope == "mcp:tools"
    assert len(provider.access_tokens) == 1
    assert len(provider.refresh_tokens) == 1


@pytest.mark.asyncio
async def test_load_access_token_found():
    provider = _make_provider()
    from mcp.server.auth.provider import AccessToken
    at = AccessToken(
        token="at-123",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) + 3600,
    )
    provider.access_tokens["at-123"] = (at, "user@outlook.com")
    result = await provider.load_access_token("at-123")
    assert result is not None
    assert result.token == "at-123"


@pytest.mark.asyncio
async def test_load_access_token_expired():
    provider = _make_provider()
    from mcp.server.auth.provider import AccessToken
    at = AccessToken(
        token="at-expired",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) - 10,
    )
    provider.access_tokens["at-expired"] = (at, "user@outlook.com")
    result = await provider.load_access_token("at-expired")
    assert result is None


@pytest.mark.asyncio
async def test_get_microsoft_token_no_account():
    provider = _make_provider()
    with pytest.raises(RuntimeError, match="No cached Microsoft token"):
        await provider.get_microsoft_token("unknown@outlook.com")


@pytest.mark.asyncio
async def test_revoke_token():
    provider = _make_provider()
    from mcp.server.auth.provider import AccessToken
    at = AccessToken(
        token="at-revoke",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) + 3600,
    )
    provider.access_tokens["at-revoke"] = (at, "user@outlook.com")
    client = _make_client()
    await provider.revoke_token(client, "access_token", "at-revoke")
    assert "at-revoke" not in provider.access_tokens


@pytest.mark.asyncio
async def test_get_user_email_for_token():
    provider = _make_provider()
    from mcp.server.auth.provider import AccessToken
    at = AccessToken(
        token="at-email",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) + 3600,
    )
    provider.access_tokens["at-email"] = (at, "user@outlook.com")
    assert provider.get_user_email_for_token("at-email") == "user@outlook.com"
    assert provider.get_user_email_for_token("nonexistent") is None


# --- Loopback redirect URI tests (RFC 8252 §7.3) ---


@pytest.mark.asyncio
async def test_get_client_returns_loopback_aware_instance():
    """get_client should return a LoopbackAwareClientInfo instance."""
    from msgraph_mcp.auth import LoopbackAwareClientInfo

    provider = _make_provider()
    client = OAuthClientInformationFull(
        client_id="loopback-client",
        client_name="Loopback Client",
        redirect_uris=[AnyUrl("http://127.0.0.1:54321/")],
    )
    await provider.register_client(client)
    result = await provider.get_client("loopback-client")
    assert isinstance(result, LoopbackAwareClientInfo)


@pytest.mark.asyncio
async def test_loopback_redirect_uri_different_port_accepted():
    """A loopback redirect URI with a different port should be accepted."""
    from msgraph_mcp.auth import LoopbackAwareClientInfo

    client = LoopbackAwareClientInfo(
        client_id="loopback-client",
        client_name="Test",
        redirect_uris=[AnyUrl("http://127.0.0.1:54321/")],
    )
    # Different port should still pass validation
    result = client.validate_redirect_uri(AnyUrl("http://127.0.0.1:64934/"))
    assert str(result) == "http://127.0.0.1:64934/"


@pytest.mark.asyncio
async def test_loopback_redirect_uri_exact_match_still_works():
    """Exact redirect URI match should still work as before."""
    from msgraph_mcp.auth import LoopbackAwareClientInfo

    client = LoopbackAwareClientInfo(
        client_id="loopback-client",
        client_name="Test",
        redirect_uris=[AnyUrl("http://127.0.0.1:54321/")],
    )
    result = client.validate_redirect_uri(AnyUrl("http://127.0.0.1:54321/"))
    assert str(result) == "http://127.0.0.1:54321/"


@pytest.mark.asyncio
async def test_loopback_localhost_different_port_accepted():
    """localhost with a different port should be accepted."""
    from msgraph_mcp.auth import LoopbackAwareClientInfo

    client = LoopbackAwareClientInfo(
        client_id="loopback-client",
        client_name="Test",
        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
    )
    result = client.validate_redirect_uri(AnyUrl("http://localhost:9999/callback"))
    assert str(result) == "http://localhost:9999/callback"


@pytest.mark.asyncio
async def test_loopback_non_loopback_uri_rejected():
    """Non-loopback URIs with wrong port should still be rejected."""
    from msgraph_mcp.auth import LoopbackAwareClientInfo
    from mcp.shared.auth import InvalidRedirectUriError

    client = LoopbackAwareClientInfo(
        client_id="test-client",
        client_name="Test",
        redirect_uris=[AnyUrl("http://example.com:3000/callback")],
    )
    with pytest.raises(InvalidRedirectUriError):
        client.validate_redirect_uri(AnyUrl("http://example.com:9999/callback"))


# --- Persistence round-trip tests (T020) ---


@pytest.mark.asyncio
async def test_token_persistence_round_trip(tmp_cache_dir):
    """Issue tokens → save → create new provider with same store → verify tokens."""
    from msgraph_mcp.store import CredentialStore

    store = CredentialStore(tmp_cache_dir)
    provider1 = _make_provider_with_store(store)

    # Simulate issuing tokens
    from mcp.server.auth.provider import AccessToken, RefreshToken
    at = AccessToken(
        token="at-persist",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) + 3600,
    )
    rt = RefreshToken(
        token="rt-persist",
        client_id="test-client",
        scopes=["mcp:tools"],
        expires_at=int(time.time()) + 86400,
    )
    provider1.access_tokens["at-persist"] = (at, "user@outlook.com")
    provider1.refresh_tokens["rt-persist"] = (rt, "user@outlook.com")
    store.save_all(provider1)

    # Create a new provider from the same store
    provider2 = _make_provider_with_store(CredentialStore(tmp_cache_dir))
    assert "at-persist" in provider2.access_tokens
    assert "rt-persist" in provider2.refresh_tokens
    loaded_at, email = provider2.access_tokens["at-persist"]
    assert loaded_at.token == "at-persist"
    assert email == "user@outlook.com"

    # Verify token is still valid via load_access_token
    result = await provider2.load_access_token("at-persist")
    assert result is not None
    assert result.token == "at-persist"


# --- Client registration persistence tests (T023) ---


@pytest.mark.asyncio
async def test_client_registration_persistence(tmp_cache_dir):
    """Register client → save → create new provider → verify get_client works."""
    from msgraph_mcp.store import CredentialStore

    store = CredentialStore(tmp_cache_dir)
    provider1 = _make_provider_with_store(store)

    client = _make_client("persist-client")
    await provider1.register_client(client)

    # Create a new provider from the same store
    provider2 = _make_provider_with_store(CredentialStore(tmp_cache_dir))
    result = await provider2.get_client("persist-client")
    assert result is not None
    assert result.client_id == "persist-client"
    assert result.client_name == "Test Client"
