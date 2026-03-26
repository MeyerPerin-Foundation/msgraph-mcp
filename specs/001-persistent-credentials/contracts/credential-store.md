# Contract: Credential Persistence Module

**Feature**: 001-persistent-credentials  
**Date**: 2026-03-26

## Module Interface: `CredentialStore`

The credential persistence module exposes a simple interface consumed by `MicrosoftOAuthProvider`. It is NOT an external API — it is an internal module contract within the server.

### Initialization

```
CredentialStore(cache_dir: Path)
```

- Creates the cache directory if it does not exist
- Sets file permissions to owner-only (0o700 for directory, 0o600 for files)
- Loads existing `credentials.json` and `msal_cache.json` if present
- On load failure: logs warning, starts with empty state

### Load Operations

```
load_clients() → dict[str, OAuthClientInformationFull]
load_access_tokens() → dict[str, tuple[AccessToken, str]]
load_refresh_tokens() → dict[str, tuple[RefreshToken, str]]
load_msal_cache() → SerializableTokenCache
```

- All load operations filter out expired entries
- Return empty collections if files are missing or corrupt

### Save Operations

```
save_clients(clients: dict[str, OAuthClientInformationFull]) → None
save_access_tokens(tokens: dict[str, tuple[AccessToken, str]]) → None
save_refresh_tokens(tokens: dict[str, tuple[RefreshToken, str]]) → None
save_msal_cache(cache: SerializableTokenCache) → None
```

- All save operations use atomic write (write to temp file, then `os.replace()`)
- MCP credentials (clients, access tokens, refresh tokens) are coalesced into a single `credentials.json` file
- MSAL cache is saved to a separate `msal_cache.json` file
- On write failure: logs warning, does not raise

### Convenience

```
save_all(provider: MicrosoftOAuthProvider) → None
```

- Saves all credential state from the provider in a single call
- Used as the common "persist after mutation" hook

## Configuration Contract

### Environment Variable

| Variable | Default | Description |
|----------|---------|-------------|
| `MSGRAPH_CACHE_DIR` | `/home/msgraph-mcp-cache` (Azure) or `.local/cache` (local) | Directory for persisted credential files |

### File Permissions

| Path | Permissions | Notes |
|------|-------------|-------|
| `{MSGRAPH_CACHE_DIR}/` | `0o700` | Owner-only directory access |
| `credentials.json` | `0o600` | Contains client secrets and bearer tokens |
| `msal_cache.json` | `0o600` | Contains Microsoft Graph tokens |

## Integration Points

### Provider Hook

The `MicrosoftOAuthProvider` calls `save_all()` after each state-mutating method:
- `register_client()`
- `exchange_authorization_code()`
- `exchange_refresh_token()`
- `revoke_token()`
- `handle_microsoft_callback()` (after MSAL token acquisition)

### Startup Hook

The `MicrosoftOAuthProvider.__init__()` calls load operations to hydrate in-memory state from disk before the server starts accepting requests.
