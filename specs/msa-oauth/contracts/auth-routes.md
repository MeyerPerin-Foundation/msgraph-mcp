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

**Query Parameters**:
- `code` (str): Authorization code from Microsoft
- `state` (str): CSRF state

**Behavior**:
1. Exchanges Microsoft auth code for Microsoft tokens via MSAL
2. Extracts user email from ID token claims
3. Validates email against `config.py` allowlist
4. Stores Microsoft tokens in MSAL cache (for Graph API calls)
5. Completes the MCP OAuth flow by redirecting to Copilot CLI's redirect URI with an MCP auth code

**Error Responses**:
- 403: User not in allowed list
- 502: Token exchange failed with Microsoft

---

## OAuthAuthorizationServerProvider Implementation

The provider bridges MCP OAuth ↔ Microsoft OAuth:

| Method | Behavior |
|--------|----------|
| `get_client(client_id)` | Returns registered MCP client info |
| `register_client(client_info)` | Stores MCP client registration (dynamic) |
| `authorize(client, params)` | Redirects to Microsoft authorize endpoint, storing MCP flow state |
| `handle_callback(...)` | Called after Microsoft redirects back, exchanges Microsoft code for tokens |
| `exchange_authorization_code(...)` | Issues MCP access token to Copilot CLI |
| `exchange_refresh_token(...)` | Refreshes MCP access token |
| `verify_access_token(token)` | Validates MCP Bearer token on each request |
