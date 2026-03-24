# Research: MSA OAuth Authentication for MCP Server

## R1: OAuth Endpoints for Consumer Accounts

- **Decision**: Use Microsoft identity platform v2.0 with `consumers` tenant
- **Authorization endpoint**: `https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize`
- **Token endpoint**: `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
- **Rationale**: The `/consumers` authority restricts to personal Microsoft accounts only, matching Constitution Principle II
- **Alternatives considered**: `/common` (rejected — allows work accounts), legacy Live SDK endpoints (deprecated)

## R2: Auth Flow

- **Decision**: Authorization code flow with PKCE, confidential client (client secret)
- **Rationale**: Server-side app can securely hold a client secret. PKCE adds defense-in-depth. Refresh tokens enable long-lived sessions without re-prompting
- **Steps**:
  1. Server generates `state`, `code_verifier`, `code_challenge`
  2. Redirect user to authorize endpoint with scopes + PKCE challenge
  3. User signs in and consents
  4. Microsoft redirects to `/auth/callback` with `code`
  5. Server exchanges code for tokens at token endpoint
  6. Validate user email against allowlist (`config.py`)
  7. Store tokens server-side, use access token for Graph calls
- **Alternatives considered**: Device code flow (rejected — requires user to visit a separate URL), client credentials (rejected — no user context)

## R3: Python Libraries

- **Decision**: `msal` for auth, `httpx` for Graph API calls
- **Rationale**: `msal` handles Microsoft-specific OAuth details (token cache, refresh, consumer authority). `httpx` is already a dev dependency and supports async
- **Alternatives considered**: `azure-identity` (rejected — designed for Azure resource auth, not consumer web flows), `requests` (rejected — no async support)

## R4: Graph API Scopes

- **Decision**: Request delegated permissions with least-privilege per tool
- **Initial scopes**: `openid profile email offline_access User.Read`
- **Tool-specific scopes** (requested at consent time):
  - Mail: `Mail.Read`
  - Calendar: `Calendars.Read`
  - To Do tasks: `Tasks.ReadWrite`
  - OneDrive: `Files.Read`
- **Rationale**: Constitution Principle III requires least-privilege scoping. `offline_access` enables refresh tokens
- **Alternatives considered**: Requesting all scopes upfront (rejected — violates least privilege)

## R5: App Registration

- **Decision**: Register as "Personal Microsoft accounts only" in Azure Portal
- **Platform**: Web
- **Redirect URI**: `https://msgraph-mcp.azurewebsites.net/auth/callback` (production), `http://localhost:8000/auth/callback` (dev)
- **Credentials**: Client secret (stored in Azure App Service app settings, never committed)
- **Rationale**: Simplest registration for consumer-only scenario

## R6: Token Storage

- **Decision**: MSAL serialized token cache, stored encrypted in Azure App Service filesystem or environment
- **Rationale**: Single-user server (allowlist is one user by default), so an in-memory MSAL cache with file-backed persistence is sufficient. For multi-user scaling, would move to encrypted Redis/DB
- **Alternatives considered**: Azure Key Vault per-token (over-engineered for single user), browser cookies (rejected — tokens must stay server-side per Constitution Principle III)

## R7: Redirect URI Pattern

- **Decision**: `https://msgraph-mcp.azurewebsites.net/auth/callback`
- **Dev**: `http://localhost:8000/auth/callback`
- **Rationale**: Standard pattern, must match registered URI exactly
