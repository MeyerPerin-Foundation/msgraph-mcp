# Auth Routes Contract

## GET /auth/login

Initiates the OAuth authorization code flow.

**Response**: 302 redirect to Microsoft authorization endpoint

**Query Parameters**: None

**Behavior**:
1. Generates PKCE code verifier + challenge
2. Generates CSRF state token
3. Stores auth state in server memory
4. Redirects to `https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize`

---

## GET /auth/callback

Handles the OAuth callback from Microsoft.

**Query Parameters**:
- `code` (str, required): Authorization code from Microsoft
- `state` (str, required): CSRF state for validation

**Success Response**: 200 JSON
```json
{
  "status": "authenticated",
  "user": "user@outlook.com"
}
```

**Error Responses**:
- 400: Missing or invalid `state` / `code`
- 403: User not in allowed list
- 502: Token exchange failed with Microsoft

**Behavior**:
1. Validates `state` against stored auth state
2. Exchanges `code` for tokens via MSAL
3. Extracts user email from ID token claims
4. Validates email against `config.py` allowlist
5. Persists MSAL token cache
6. Returns authenticated user info

---

## GET /auth/logout

Clears the server-side token cache.

**Response**: 200 JSON
```json
{
  "status": "logged_out"
}
```

---

## GET /auth/status

Returns current authentication status.

**Response**: 200 JSON
```json
{
  "authenticated": true,
  "user": "user@outlook.com"
}
```
or
```json
{
  "authenticated": false,
  "user": null
}
```
