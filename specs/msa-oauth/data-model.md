# Data Model: MSA OAuth Authentication

## Entities

### AuthConfig
Configuration for the OAuth flow. Loaded from environment variables.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| client_id | str | `MSGRAPH_CLIENT_ID` env var | Azure app registration client ID |
| client_secret | str | `MSGRAPH_CLIENT_SECRET` env var | Azure app registration client secret |
| redirect_uri | str | `MSGRAPH_REDIRECT_URI` env var | Microsoft OAuth callback URL (server's internal route) |
| authority | str | constant | `https://login.microsoftonline.com/consumers` |
| scopes | list[str] | constant + config | Microsoft Graph scopes |

### MCP OAuth State (managed by OAuthAuthorizationServerProvider)

All state is held **in-memory**. Server restart clears all state — MCP clients
must re-register and users must re-authenticate. This is acceptable for a
single-user deployment. For production scaling, move to persistent storage
(encrypted Redis or database).

| Field | Type | Description |
|-------|------|-------------|
| registered_clients | dict | MCP clients registered via dynamic registration (RFC 7591) |
| pending_flows | dict | In-flight OAuth flows: `{microsoft_state: {mcp_redirect_uri, mcp_code_challenge, mcp_state, client_id}}` |
| auth_codes | dict | `{code_str: AuthorizationCode(code, scopes, expires_at, client_id, code_challenge, redirect_uri) + user_email}` |
| access_tokens | dict | `{token_str: AccessToken(token, client_id, scopes, expires_at) + user_email}` |
| refresh_tokens | dict | `{token_str: RefreshToken(token, client_id, scopes, expires_at) + user_email}` |
| microsoft_token_cache | SerializableTokenCache | MSAL cache for Microsoft access + refresh tokens |

### MCP Flow Mapping

The provider bridges two OAuth flows:

| MCP OAuth (Copilot CLI ↔ Server) | Microsoft OAuth (Server ↔ Microsoft) |
|----------------------------------|--------------------------------------|
| Client registers via `/register` | N/A |
| Client redirected to `/authorize` | Server redirects to Microsoft `/authorize` |
| N/A | Microsoft redirects to `/auth/microsoft/callback` |
| Server issues MCP auth code | Server exchanges Microsoft code for tokens |
| Client exchanges code at `/token` | Server returns MCP access token |
| Client sends Bearer token | Server uses stored Microsoft token for Graph calls |

## State Transitions

```
No MCP Client → [POST /register] → Client Registered
    → [GET /authorize] → Redirected to Microsoft
    → [Microsoft callback] → Microsoft tokens acquired
    → [MCP auth code issued] → Client exchanges at /token
    → [MCP access token issued] → Authenticated
    → [token expired] → Client refreshes at /token → Authenticated
    → [Microsoft refresh failed] → 401 on next Graph call
```
