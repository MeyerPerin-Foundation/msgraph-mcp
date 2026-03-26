# Data Model: Persistent Credential Cache

**Feature**: 001-persistent-credentials  
**Date**: 2026-03-26

## Entities

### CredentialStore

The top-level container for all persisted MCP credential state. Serialized as a single JSON file.

**Fields**:
- `version` (string): Schema version for forward compatibility (e.g., `"1"`)
- `registered_clients` (dict[string, RegisteredClient]): Keyed by `client_id`
- `access_tokens` (dict[string, StoredAccessToken]): Keyed by token string
- `refresh_tokens` (dict[string, StoredRefreshToken]): Keyed by token string

### RegisteredClient

A dynamically registered MCP OAuth client, as received from the FastMCP registration handler.

**Fields**:
- All fields from `OAuthClientInformationFull` (client_id, client_secret, redirect_uris, scope, grant_types, response_types, client_name, token_endpoint_auth_method, client_id_issued_at, client_secret_expires_at, etc.)

**Serialization**: Direct Pydantic `model_dump(mode="json")` / `model_validate()` round-trip.

### StoredAccessToken

An MCP access token with its associated user email, persisted for restart survival.

**Fields**:
- `token` (string): The bearer token string (also the dict key)
- `client_id` (string): The client this token was issued to
- `scopes` (list[string]): Granted scopes
- `expires_at` (int | None): Unix timestamp of expiration
- `user_email` (string): The Microsoft account email associated with this token

**Validation on load**: Discard if `expires_at` is in the past.

### StoredRefreshToken

An MCP refresh token with its associated user email, persisted for restart survival.

**Fields**:
- `token` (string): The refresh token string (also the dict key)
- `client_id` (string): The client this token was issued to
- `scopes` (list[string]): Granted scopes
- `expires_at` (int | None): Unix timestamp of expiration
- `user_email` (string): The Microsoft account email associated with this token

**Validation on load**: Discard if `expires_at` is in the past.

### MSAL Token Cache (separate file)

The serialized output of `msal.SerializableTokenCache.serialize()`. This is an opaque JSON string managed entirely by MSAL. It is stored in a separate file (`msal_cache.json`) to avoid coupling with the MCP credential schema.

**Persistence trigger**: Written whenever `_msal_cache.has_state_changed` is `True` after a token operation.

## Relationships

```
CredentialStore
├── registered_clients: {client_id → RegisteredClient}
├── access_tokens: {token → StoredAccessToken}
│   └── StoredAccessToken.client_id → RegisteredClient
│   └── StoredAccessToken.user_email → (used to look up MSAL accounts)
└── refresh_tokens: {token → StoredRefreshToken}
    └── StoredRefreshToken.client_id → RegisteredClient
    └── StoredRefreshToken.user_email → (used to look up MSAL accounts)

MSAL Token Cache (separate file)
└── Contains Microsoft Graph access/refresh tokens and account metadata
└── Linked to MCP tokens via user_email
```

## State That Is NOT Persisted

- **pending_flows**: In-flight OAuth authorization flows. These contain MSAL flow objects with internal state tied to a specific browser interaction. They expire in minutes and cannot meaningfully survive a restart.
- **auth_codes**: MCP authorization codes. Short-lived (5 minutes), single-use, and tied to an active browser redirect flow.

## File Layout

```
{MSGRAPH_CACHE_DIR}/
├── credentials.json     # CredentialStore serialized as JSON
└── msal_cache.json      # MSAL SerializableTokenCache serialized as JSON
```
