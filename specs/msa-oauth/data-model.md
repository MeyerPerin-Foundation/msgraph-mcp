# Data Model: MSA OAuth Authentication

## Entities

### AuthConfig
Configuration for the OAuth flow. Loaded from environment variables.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| client_id | str | `MSGRAPH_CLIENT_ID` env var | Azure app registration client ID |
| client_secret | str | `MSGRAPH_CLIENT_SECRET` env var | Azure app registration client secret |
| redirect_uri | str | `MSGRAPH_REDIRECT_URI` env var | OAuth callback URL |
| authority | str | constant | `https://login.microsoftonline.com/consumers` |
| scopes | list[str] | constant + config | Base scopes + tool-specific scopes |

### TokenCache
MSAL serialized token cache persisted server-side.

| Field | Type | Description |
|-------|------|-------------|
| cache_data | str | MSAL serialized cache (JSON blob) |
| user_email | str | Email of authenticated user |
| last_refreshed | datetime | Last token refresh timestamp |

### AuthState
In-memory session state during the OAuth flow.

| Field | Type | Description |
|-------|------|-------------|
| state | str | CSRF protection nonce |
| code_verifier | str | PKCE code verifier |
| flow | dict | MSAL auth code flow object |

## Relationships

- `AuthConfig` → configures → MSAL `ConfidentialClientApplication`
- `TokenCache` → stored per → allowed user (from `config.py` allowlist)
- `AuthState` → temporary during → OAuth login flow

## State Transitions

```
Unauthenticated → [GET /auth/login] → Redirected to Microsoft
    → [GET /auth/callback] → Token acquired → Authenticated
    → [token expired] → [MSAL auto-refresh] → Authenticated
    → [refresh failed] → Unauthenticated
    → [GET /auth/logout] → Cache cleared → Unauthenticated
```
