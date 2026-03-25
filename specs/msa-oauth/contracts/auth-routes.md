# Auth Contracts

## MCP-Native OAuth (handled by FastMCP automatically)

FastMCP auto-creates these endpoints when `auth` and `auth_server_provider` are configured.
No custom route implementation needed.

### GET /.well-known/oauth-protected-resource (RFC 9728)

Auto-served by FastMCP. Tells Copilot CLI how to authenticate.

**Response**: 200 JSON
```json
{
  "resource": "https://msgraph-mcp.azurewebsites.net",
  "authorization_servers": ["https://msgraph-mcp.azurewebsites.net"],
  "scopes_supported": ["mcp:tools"]
}
```

### GET /.well-known/oauth-authorization-server (RFC 8414)

Auto-served by FastMCP. Advertises OAuth endpoints.

### POST /authorize

Auto-served by FastMCP. Delegates to `OAuthAuthorizationServerProvider.authorize()`,
which redirects to Microsoft's authorize endpoint.

### POST /token

Auto-served by FastMCP. Delegates to `OAuthAuthorizationServerProvider.exchange_authorization_code()`
and `exchange_refresh_token()`.

### POST /register (RFC 7591 Dynamic Client Registration)

Auto-served by FastMCP. Delegates to `OAuthAuthorizationServerProvider.register_client()`.

---

## Custom Server Routes

### GET /auth/microsoft/callback

Internal route — handles Microsoft's OAuth redirect back to the server.
**Must be registered as a custom Starlette route** via
`mcp._custom_starlette_routes.append(Route("/auth/microsoft/callback", handler))`,
the same way the `/` health route is registered.

**Query Parameters**:
- `code` (str): Authorization code from Microsoft
- `state` (str): CSRF state (maps to stored MCP flow state)

**Cross-Request State Management**:

When `authorize()` is called, the provider stores:
```python
pending_flows[microsoft_state] = {
    "mcp_redirect_uri": params.redirect_uri,   # Copilot CLI's callback
    "mcp_code_challenge": params.code_challenge,
    "mcp_state": params.state,                  # Copilot CLI's CSRF state
}
```
When Microsoft redirects back, the `state` parameter is used to look up this context.

**Behavior**:
1. Looks up `state` in `pending_flows` to retrieve the original MCP flow context
2. Exchanges Microsoft auth code for Microsoft tokens via MSAL
3. Extracts user email from ID token claims
4. Validates email against `config.py` allowlist
5. Stores Microsoft tokens in MSAL cache keyed by user email
6. Generates an MCP authorization code (>=160 bits entropy), stores it mapped to user email
7. Redirects to the MCP client's `redirect_uri` with `code={mcp_auth_code}&state={mcp_state}`

**Error Responses**:
- 403: User not in allowed list
- 502: Token exchange failed with Microsoft

---

## OAuthAuthorizationServerProvider Implementation

The provider bridges MCP OAuth and Microsoft OAuth. Methods match the
`OAuthAuthorizationServerProvider` protocol from `mcp.server.auth.provider`.

| Method | Signature | Behavior |
|--------|-----------|----------|
| `get_client` | `(client_id: str) → OAuthClientInformationFull \| None` | Returns registered MCP client info from `registered_clients` dict |
| `register_client` | `(client_info: OAuthClientInformationFull) → None` | Stores MCP client registration in `registered_clients` dict |
| `authorize` | `(client, params: AuthorizationParams) → str` | Stores MCP flow context in `pending_flows[microsoft_state]`, returns Microsoft authorize URL |
| `load_authorization_code` | `(client, authorization_code: str) → AuthorizationCode \| None` | Looks up `auth_codes[code]`, returns `AuthorizationCode` with `code`, `scopes`, `expires_at`, `client_id`, `code_challenge`, `redirect_uri` |
| `exchange_authorization_code` | `(client, authorization_code: AuthorizationCode) → OAuthToken` | Consumes auth code, issues MCP access + refresh tokens, maps them to user email in `access_tokens` and `refresh_tokens` dicts |
| `load_refresh_token` | `(client, refresh_token: str) → RefreshToken \| None` | Looks up `refresh_tokens[token]`, returns `RefreshToken` if found |
| `exchange_refresh_token` | `(client, refresh_token: RefreshToken, scopes: list[str]) → OAuthToken` | Rotates MCP access + refresh tokens, preserves user email mapping |
| `load_access_token` | `(token: str) → AccessToken \| None` | Looks up `access_tokens[token]`, returns `AccessToken` with `client_id`, `scopes`, `expires_at` |
| `revoke_token` | `(client, token_type, token: str) → None` | Removes token from `access_tokens` or `refresh_tokens`. Single-user server — no-op is also acceptable |

---

## How MCP Tools Access Microsoft Graph Tokens

When an MCP tool is invoked by Copilot CLI, FastMCP validates the Bearer token via `verify_access_token()` and injects auth context into the request scope.

**Token lookup chain**:

```
Copilot CLI request (Bearer: mcp_token_xyz)
    → FastMCP middleware calls verify_access_token("mcp_token_xyz")
    → Provider returns AccessToken(client_id=..., scopes=[...])
    → Provider also stores mapping: mcp_token_xyz → user_email
    → Tool implementation calls provider.get_microsoft_token(user_email)
    → Provider looks up MSAL cache for user_email
    → Returns Microsoft access_token (refreshing via MSAL if expired)
    → Tool uses Microsoft access_token to call Graph API via httpx
```

**Implementation in tools**:

```python
@mcp.tool()
async def read_mail(ctx: Context) -> str:
    # Get the auth context from the current request
    user_email = get_authenticated_user(ctx)
    ms_token = await auth_provider.get_microsoft_token(user_email)
    # Call Graph API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me/messages",
            headers={"Authorization": f"Bearer {ms_token}"},
        )
    return response.text
```

The provider exposes `get_microsoft_token(user_email)` which uses MSAL's
`acquire_token_silent()` to get a valid token (refreshing automatically if expired).
