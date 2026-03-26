"""Tests for the CredentialStore persistence module."""

import json
import os
import platform
import time

import msal
import pytest
from pydantic import AnyUrl

from mcp.server.auth.provider import AccessToken, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull

from msgraph_mcp.store import CredentialStore


# --- Helpers ---


def _make_client(client_id: str = "test-client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_name="Test Client",
        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
    )


def _make_access_token(
    token: str = "at-1",
    client_id: str = "test-client",
    expires_at: int | None = None,
) -> AccessToken:
    return AccessToken(
        token=token,
        client_id=client_id,
        scopes=["mcp:tools"],
        expires_at=expires_at or int(time.time()) + 3600,
    )


def _make_refresh_token(
    token: str = "rt-1",
    client_id: str = "test-client",
    expires_at: int | None = None,
) -> RefreshToken:
    return RefreshToken(
        token=token,
        client_id=client_id,
        scopes=["mcp:tools"],
        expires_at=expires_at or int(time.time()) + 86400,
    )


# --- Round-trip tests ---


def test_save_load_clients_round_trip(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    client = _make_client("c1")
    store.save_credentials({"c1": client}, {}, {})

    clients, at, rt = store.load_credentials()
    assert "c1" in clients
    assert clients["c1"].client_id == "c1"
    assert clients["c1"].client_name == "Test Client"
    assert len(at) == 0
    assert len(rt) == 0


def test_save_load_access_tokens_round_trip(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    at_obj = _make_access_token("at-1")
    store.save_credentials({}, {"at-1": (at_obj, "user@example.com")}, {})

    clients, at, rt = store.load_credentials()
    assert "at-1" in at
    loaded_at, email = at["at-1"]
    assert loaded_at.token == "at-1"
    assert email == "user@example.com"


def test_save_load_refresh_tokens_round_trip(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    rt_obj = _make_refresh_token("rt-1")
    store.save_credentials({}, {}, {"rt-1": (rt_obj, "user@example.com")})

    clients, at, rt = store.load_credentials()
    assert "rt-1" in rt
    loaded_rt, email = rt["rt-1"]
    assert loaded_rt.token == "rt-1"
    assert email == "user@example.com"


def test_msal_cache_round_trip(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    cache = msal.SerializableTokenCache()
    # Simulate a state change so save_msal_cache writes
    cache.has_state_changed = True
    store.save_msal_cache(cache)

    loaded = store.load_msal_cache()
    assert isinstance(loaded, msal.SerializableTokenCache)


def test_msal_cache_skip_write_when_unchanged(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    cache = msal.SerializableTokenCache()
    # has_state_changed is False by default
    store.save_msal_cache(cache)
    assert not store._msal_cache_path.exists()


# --- Expired token filtering ---


def test_expired_access_tokens_filtered_on_load(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    valid = _make_access_token("at-valid", expires_at=int(time.time()) + 3600)
    expired = _make_access_token("at-expired", expires_at=int(time.time()) - 10)

    store.save_credentials(
        {},
        {
            "at-valid": (valid, "u@e.com"),
            "at-expired": (expired, "u@e.com"),
        },
        {},
    )

    _clients, at, _rt = store.load_credentials()
    assert "at-valid" in at
    assert "at-expired" not in at


def test_expired_refresh_tokens_filtered_on_load(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    valid = _make_refresh_token("rt-valid", expires_at=int(time.time()) + 86400)
    expired = _make_refresh_token("rt-expired", expires_at=int(time.time()) - 10)

    store.save_credentials(
        {},
        {},
        {
            "rt-valid": (valid, "u@e.com"),
            "rt-expired": (expired, "u@e.com"),
        },
    )

    _clients, _at, rt = store.load_credentials()
    assert "rt-valid" in rt
    assert "rt-expired" not in rt


# --- Corrupt file handling ---


def test_corrupt_credentials_returns_empty(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    store._credentials_path.write_text("not json at all", encoding="utf-8")

    clients, at, rt = store.load_credentials()
    assert clients == {}
    assert at == {}
    assert rt == {}


def test_corrupt_msal_cache_returns_fresh(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    store._msal_cache_path.write_text("not json", encoding="utf-8")

    cache = store.load_msal_cache()
    assert isinstance(cache, msal.SerializableTokenCache)


# --- Write failure handling ---


@pytest.mark.skipif(platform.system() == "Windows", reason="chmod not reliable on Windows")
def test_write_failure_readonly_dir(tmp_path: object) -> None:
    import pathlib

    cache_dir = pathlib.Path(str(tmp_path)) / "readonly_cache"
    cache_dir.mkdir()
    store = CredentialStore(cache_dir)
    # Make dir read-only
    os.chmod(cache_dir, 0o500)
    try:
        with pytest.raises(OSError):
            store.save_credentials({"c1": _make_client("c1")}, {}, {})
    finally:
        os.chmod(cache_dir, 0o700)


# --- File permissions ---


@pytest.mark.skipif(platform.system() == "Windows", reason="chmod not reliable on Windows")
def test_file_permissions_0o600(tmp_path: object) -> None:
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    store.save_credentials({"c1": _make_client("c1")}, {}, {})
    stat = os.stat(store._credentials_path)
    assert oct(stat.st_mode & 0o777) == oct(0o600)


# --- FR-005 negative test: no pending_flows or auth_codes ---


def test_pending_flows_and_auth_codes_not_persisted(tmp_path: object) -> None:
    """Verify that pending_flows and auth_codes are NOT in credentials.json."""
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    client = _make_client("c1")
    at = _make_access_token("at-1")
    rt = _make_refresh_token("rt-1")
    store.save_credentials(
        {"c1": client},
        {"at-1": (at, "u@e.com")},
        {"rt-1": (rt, "u@e.com")},
    )

    raw = json.loads(store._credentials_path.read_text(encoding="utf-8"))
    assert "pending_flows" not in raw
    assert "auth_codes" not in raw


# --- Client deserialization with all fields (T022) ---


def test_client_round_trip_all_fields(tmp_path: object) -> None:
    """Verify OAuthClientInformationFull survives serialization with extra fields."""
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    client = OAuthClientInformationFull(
        client_id="full-client",
        client_name="Full Client",
        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
        scope="mcp:tools openid",
        grant_types=["authorization_code", "refresh_token"],
    )
    store.save_credentials({"full-client": client}, {}, {})

    clients, _at, _rt = store.load_credentials()
    loaded = clients["full-client"]
    assert loaded.client_id == "full-client"
    assert loaded.client_name == "Full Client"
    assert loaded.scope == "mcp:tools openid"


# --- Revocation persistence (T026) ---


def test_revoked_token_not_in_persisted_file(tmp_path: object) -> None:
    """Confirm a revoked token is absent from the persisted file after save."""
    store = CredentialStore(tmp_path)  # type: ignore[arg-type]
    at1 = _make_access_token("at-keep")
    at2 = _make_access_token("at-revoke")
    tokens: dict[str, tuple[AccessToken, str]] = {
        "at-keep": (at1, "u@e.com"),
        "at-revoke": (at2, "u@e.com"),
    }
    # Simulate revocation by removing from in-memory state
    del tokens["at-revoke"]
    store.save_credentials({}, tokens, {})

    _c, loaded_at, _r = store.load_credentials()
    assert "at-keep" in loaded_at
    assert "at-revoke" not in loaded_at
