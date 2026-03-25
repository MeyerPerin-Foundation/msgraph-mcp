# Research: MSA OAuth Authentication for MCP Server

## R1: MCP Authorization Specification (Critical Finding)

- **Decision**: Implement MCP-native OAuth using FastMCP's built-in auth support
- **Key insight**: The MCP spec (2025-03-26) defines how HTTP MCP servers MUST implement authorization. Copilot CLI implements this protocol — it discovers auth requirements via RFC 9728 Protected Resource Metadata, then drives the OAuth flow itself
- **Server role**: OAuth **Authorization Server + Resource Server** — proxies to Microsoft for user login, acquires and stores Microsoft tokens server-side, issues its own MCP tokens to Copilot CLI
- **Client role**: Copilot CLI discovers auth via metadata, drives MCP OAuth flow, sends Bearer tokens on MCP requests
- **FastMCP support**: Two options:
  - `OAuthAuthorizationServerProvider` — server is both AS + RS, proxies to Microsoft (complex)
  - `TokenVerifier` — server only validates tokens (simpler, but Copilot CLI needs to know where to get tokens)
- **Decision**: Use `OAuthAuthorizationServerProvider` because the MCP client (Copilot CLI) needs an authorization server to talk to, and Microsoft's authorize endpoint can't act as the MCP AS directly (different protocols). The MCP server will proxy: MCP OAuth AS ↔ Microsoft OAuth
- **Alternatives rejected**: Custom `/auth/*` routes (not MCP-native, Copilot CLI won't use them)

## R2: OAuth Endpoints for Consumer Accounts

- **Authorization endpoint**: `https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize`
- **Token endpoint**: `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
- **Rationale**: The `/consumers` authority restricts to personal Microsoft accounts only, matching Constitution Principle II

## R3: Auth Architecture

```
+──────────────+     MCP OAuth     +──────────────+     Microsoft OAuth     +───────────────+
│  Copilot CLI │ ←──────────────→  │  MCP Server  │ ←────────────────────→  │  Microsoft    │
│  (MCP Client)│                   │  (AS + RS)   │                         │  login.ms.com │
+──────────────+                   +──────────────+                         +───────────────+
```

1. Copilot CLI discovers server auth via `/.well-known/oauth-protected-resource`
2. Copilot CLI initiates OAuth with MCP server's `/authorize` endpoint
3. MCP server redirects to Microsoft's authorize endpoint
4. User signs in to Microsoft, consents
5. Microsoft redirects back to MCP server with auth code
6. MCP server exchanges code with Microsoft for tokens
7. MCP server issues its own auth code to Copilot CLI
8. Copilot CLI exchanges code at MCP server's `/token` endpoint
9. MCP server issues access token to Copilot CLI
10. Copilot CLI sends Bearer token on all subsequent MCP requests

## R4: FastMCP Auth API

- `FastMCP(auth=AuthSettings(...), auth_server_provider=MyProvider())`
- `AuthSettings`: `issuer_url`, `resource_server_url`, `required_scopes`, `client_registration_options`
- `OAuthAuthorizationServerProvider`: Protocol with methods `get_client`, `register_client`, `authorize`, `handle_callback`, `exchange_authorization_code`, `exchange_refresh_token`, `verify_access_token`
- FastMCP auto-creates `/.well-known/oauth-protected-resource`, `/.well-known/oauth-authorization-server`, `/authorize`, `/token`, `/register` routes

## R5: Python Libraries

- **Decision**: `msal` for the server's upstream OAuth with Microsoft, `httpx` for Graph API calls
- **Rationale**: `msal` handles token cache, refresh, PKCE with Microsoft. The MCP SDK handles the downstream OAuth with Copilot CLI

## R6: Graph API Scopes

- **Decision**: Request all scopes upfront at consent time
- **Full scope set**: `openid profile email offline_access User.Read Mail.Read Calendars.Read Tasks.ReadWrite Files.Read`
- **Rationale**: Microsoft consumer accounts (MSA) do not reliably support incremental consent. All scopes must be requested in the initial authorization request. Constitution Principle III (least privilege) is satisfied by requesting only the scopes the server's tools actually use
- **Note**: If new tools are added requiring additional scopes, the scope list must be updated and existing users will need to re-consent

## R7: App Registration

- **Decision**: Register as "Personal Microsoft accounts only" in Azure Portal
- **Redirect URI**: `https://msgraph-mcp.azurewebsites.net/auth/microsoft/callback` (server's internal route for Microsoft's redirect)
- **Credentials**: Client secret (stored in Azure App Service app settings)

## R8: Token Storage

- **Decision**: Server stores Microsoft tokens (access + refresh) in MSAL cache for Graph API calls. Server issues its own short-lived tokens to Copilot CLI
- **Rationale**: Server needs Microsoft tokens to call Graph. Copilot CLI tokens are validated per-request

## R9: MCP Config for Copilot CLI

- **Decision**: Copilot CLI config remains `{"type":"http","url":"..."}`. Auth discovery happens automatically via `/.well-known/oauth-protected-resource` endpoint (RFC 9728)
- **Rationale**: MCP spec mandates metadata-driven discovery
