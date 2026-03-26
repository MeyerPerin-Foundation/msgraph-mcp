"""Persistent credential store for MCP OAuth tokens and MSAL cache."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import msal
from mcp.server.auth.provider import AccessToken, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull

if TYPE_CHECKING:
    from msgraph_mcp.auth import MicrosoftOAuthProvider

logger = logging.getLogger(__name__)

CREDENTIALS_FILE = "credentials.json"
MSAL_CACHE_FILE = "msal_cache.json"
CREDENTIAL_FORMAT_VERSION = "1"


class CredentialStore:
    """Persists MCP credentials and MSAL token cache to disk.

    Uses atomic writes and restrictive file permissions (0o600) to
    protect credential data at rest.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._cache_dir, 0o700)
        except OSError:
            logger.debug("Could not set directory permissions on %s", self._cache_dir)
        self._credentials_path = self._cache_dir / CREDENTIALS_FILE
        self._msal_cache_path = self._cache_dir / MSAL_CACHE_FILE

    # --- Low-level helpers ---

    def _atomic_write(self, path: Path, data: str) -> None:
        """Write data to *path* atomically via temp file + os.replace()."""
        fd, tmp_path = tempfile.mkstemp(dir=self._cache_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            try:
                os.chmod(tmp_path, 0o600)
            except OSError:
                logger.debug("Could not set file permissions on %s", tmp_path)
            os.replace(tmp_path, path)
        except Exception:
            # Clean up the temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _load_json(self, path: Path) -> dict:
        """Read JSON from *path*, returning ``{}`` on any error."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            if path.exists():
                logger.warning("Failed to load %s: %s", path, exc)
            return {}

    # --- Credential persistence ---

    def save_credentials(
        self,
        clients: dict[str, OAuthClientInformationFull],
        access_tokens: dict[str, tuple[AccessToken, str]],
        refresh_tokens: dict[str, tuple[RefreshToken, str]],
    ) -> None:
        """Serialize registered clients, access tokens, and refresh tokens."""
        payload: dict = {
            "version": CREDENTIAL_FORMAT_VERSION,
            "registered_clients": {
                cid: info.model_dump(mode="json") for cid, info in clients.items()
            },
            "access_tokens": {
                tok: {
                    "token_data": at.model_dump(mode="json"),
                    "user_email": email,
                }
                for tok, (at, email) in access_tokens.items()
            },
            "refresh_tokens": {
                tok: {
                    "token_data": rt.model_dump(mode="json"),
                    "user_email": email,
                }
                for tok, (rt, email) in refresh_tokens.items()
            },
        }
        self._atomic_write(self._credentials_path, json.dumps(payload, indent=2))

    def load_credentials(
        self,
    ) -> tuple[
        dict[str, OAuthClientInformationFull],
        dict[str, tuple[AccessToken, str]],
        dict[str, tuple[RefreshToken, str]],
    ]:
        """Deserialize credentials, filtering out expired tokens."""
        data = self._load_json(self._credentials_path)
        if not data:
            return {}, {}, {}

        now = time.time()

        clients: dict[str, OAuthClientInformationFull] = {}
        for cid, cdata in data.get("registered_clients", {}).items():
            try:
                clients[cid] = OAuthClientInformationFull.model_validate(cdata)
            except Exception as exc:
                logger.warning("Skipping invalid client %s: %s", cid, exc)

        access_tokens: dict[str, tuple[AccessToken, str]] = {}
        for tok, entry in data.get("access_tokens", {}).items():
            try:
                at = AccessToken.model_validate(entry["token_data"])
                if at.expires_at and at.expires_at < now:
                    continue
                access_tokens[tok] = (at, entry["user_email"])
            except Exception as exc:
                logger.warning("Skipping invalid access token: %s", exc)

        refresh_tokens: dict[str, tuple[RefreshToken, str]] = {}
        for tok, entry in data.get("refresh_tokens", {}).items():
            try:
                rt = RefreshToken.model_validate(entry["token_data"])
                if rt.expires_at and rt.expires_at < now:
                    continue
                refresh_tokens[tok] = (rt, entry["user_email"])
            except Exception as exc:
                logger.warning("Skipping invalid refresh token: %s", exc)

        return clients, access_tokens, refresh_tokens

    # --- MSAL cache persistence ---

    def save_msal_cache(self, cache: msal.SerializableTokenCache) -> None:
        """Persist the MSAL token cache if it has changed."""
        if not cache.has_state_changed:
            return
        self._atomic_write(self._msal_cache_path, cache.serialize())
        cache.has_state_changed = False

    def load_msal_cache(self) -> msal.SerializableTokenCache:
        """Load the MSAL token cache from disk, returning a fresh cache on error."""
        cache = msal.SerializableTokenCache()
        data = self._load_json(self._msal_cache_path)
        if data:
            try:
                cache.deserialize(json.dumps(data))
            except Exception as exc:
                logger.warning("Failed to deserialize MSAL cache: %s", exc)
                cache = msal.SerializableTokenCache()
        return cache

    # --- Convenience ---

    def save_all(self, provider: MicrosoftOAuthProvider) -> None:
        """Save all credentials and the MSAL cache in one call."""
        self.save_credentials(
            provider.registered_clients,
            provider.access_tokens,
            provider.refresh_tokens,
        )
        self.save_msal_cache(provider._msal_cache)
