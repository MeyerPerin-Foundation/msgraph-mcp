"""OAuth authorization server provider bridging MCP OAuth with Microsoft OAuth."""

import secrets
import time

import msal
from pydantic import AnyUrl
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthClientInformationFull,
    OAuthToken,
    RefreshToken,
    TokenError,
)

from msgraph_mcp.config import (
    GRAPH_SCOPES,
    MICROSOFT_AUTHORITY,
    MSGRAPH_CLIENT_ID,
    MSGRAPH_CLIENT_SECRET,
    MSGRAPH_REDIRECT_URI,
    is_user_allowed,
)

# MCP auth code / token lifetime
AUTH_CODE_LIFETIME_SECONDS = 300  # 5 minutes
ACCESS_TOKEN_LIFETIME_SECONDS = 3600  # 1 hour
REFRESH_TOKEN_LIFETIME_SECONDS = 86400  # 24 hours


class MicrosoftOAuthProvider:
    """Bridges MCP OAuth (Copilot CLI ↔ server) with Microsoft OAuth (server ↔ Microsoft).

    Implements the OAuthAuthorizationServerProvider protocol from FastMCP.
    """

    def __init__(self) -> None:
        self.registered_clients: dict[str, OAuthClientInformationFull] = {}
        self.pending_flows: dict[str, dict] = {}
        self.auth_codes: dict[str, tuple[AuthorizationCode, str]] = {}  # code → (AuthorizationCode, user_email)
        self.access_tokens: dict[str, tuple[AccessToken, str]] = {}  # token → (AccessToken, user_email)
        self.refresh_tokens: dict[str, tuple[RefreshToken, str]] = {}  # token → (RefreshToken, user_email)

        self._msal_cache = msal.SerializableTokenCache()
        self._msal_app = msal.ConfidentialClientApplication(
            client_id=MSGRAPH_CLIENT_ID,
            client_credential=MSGRAPH_CLIENT_SECRET,
            authority=MICROSOFT_AUTHORITY,
            token_cache=self._msal_cache,
        )

    # --- Client Registration (RFC 7591) ---

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Retrieve a registered MCP client."""
        return self.registered_clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Store an MCP client registration."""
        self.registered_clients[client_info.client_id] = client_info

    # --- Authorization ---

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Redirect to Microsoft's authorize endpoint, storing MCP flow context."""
        microsoft_state = secrets.token_urlsafe(32)

        self.pending_flows[microsoft_state] = {
            "mcp_redirect_uri": str(params.redirect_uri),
            "mcp_code_challenge": params.code_challenge,
            "mcp_state": params.state,
            "client_id": client.client_id,
        }

        # Build Microsoft authorize URL using MSAL's auth code flow
        flow = self._msal_app.initiate_auth_code_flow(
            scopes=GRAPH_SCOPES,
            redirect_uri=MSGRAPH_REDIRECT_URI,
            state=microsoft_state,
        )
        # Store the MSAL flow object for token exchange later
        self.pending_flows[microsoft_state]["msal_flow"] = flow
        return flow["auth_uri"]

    # --- Microsoft Callback (custom route) ---

    async def handle_microsoft_callback(self, request: Request) -> RedirectResponse | JSONResponse:
        """Handle Microsoft's OAuth redirect back to the server."""
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        if error:
            return JSONResponse(
                {"error": "microsoft_auth_failed", "detail": request.query_params.get("error_description", error)},
                status_code=502,
            )

        if not code or not state:
            return JSONResponse({"error": "missing_params"}, status_code=400)

        # Look up the MCP flow context
        flow_context = self.pending_flows.pop(state, None)
        if not flow_context:
            return JSONResponse({"error": "invalid_state"}, status_code=400)

        # Exchange Microsoft auth code for tokens using the stored flow
        msal_flow = flow_context.get("msal_flow", {})
        auth_response = dict(request.query_params)
        result = self._msal_app.acquire_token_by_auth_code_flow(
            auth_code_flow=msal_flow,
            auth_response=auth_response,
        )

        if "error" in result:
            return JSONResponse(
                {"error": "token_exchange_failed", "detail": result.get("error_description", result["error"])},
                status_code=502,
            )

        # Extract user email from ID token claims
        id_token_claims = result.get("id_token_claims", {})
        user_email = (
            id_token_claims.get("preferred_username")
            or id_token_claims.get("email")
            or ""
        )

        if not user_email or not is_user_allowed(user_email):
            return JSONResponse(
                {"error": "user_not_allowed", "user": user_email},
                status_code=403,
            )

        # Generate MCP authorization code (>=160 bits entropy)
        mcp_auth_code = secrets.token_urlsafe(32)
        now = time.time()

        auth_code_obj = AuthorizationCode(
            code=mcp_auth_code,
            scopes=["mcp:tools"],
            expires_at=now + AUTH_CODE_LIFETIME_SECONDS,
            client_id=flow_context["client_id"],
            code_challenge=flow_context["mcp_code_challenge"],
            redirect_uri=AnyUrl(flow_context["mcp_redirect_uri"]),
            redirect_uri_provided_explicitly=True,
        )
        self.auth_codes[mcp_auth_code] = (auth_code_obj, user_email)

        # Redirect to MCP client's redirect_uri
        redirect_uri = flow_context["mcp_redirect_uri"]
        separator = "&" if "?" in redirect_uri else "?"
        params_str = f"code={mcp_auth_code}"
        if flow_context["mcp_state"]:
            params_str += f"&state={flow_context['mcp_state']}"

        return RedirectResponse(f"{redirect_uri}{separator}{params_str}", status_code=302)

    # --- Authorization Code Exchange ---

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        """Look up an MCP authorization code."""
        entry = self.auth_codes.get(authorization_code)
        if not entry:
            return None
        auth_code_obj, _user_email = entry
        if time.time() > auth_code_obj.expires_at:
            self.auth_codes.pop(authorization_code, None)
            return None
        return auth_code_obj

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Consume an MCP auth code and issue MCP access + refresh tokens."""
        entry = self.auth_codes.pop(authorization_code.code, None)
        if not entry:
            raise TokenError(error="invalid_grant", error_description="Authorization code not found")
        _auth_code_obj, user_email = entry

        now = int(time.time())
        access_token_str = secrets.token_urlsafe(32)
        refresh_token_str = secrets.token_urlsafe(32)

        access_token = AccessToken(
            token=access_token_str,
            client_id=client.client_id,
            scopes=["mcp:tools"],
            expires_at=now + ACCESS_TOKEN_LIFETIME_SECONDS,
        )
        refresh_token = RefreshToken(
            token=refresh_token_str,
            client_id=client.client_id,
            scopes=["mcp:tools"],
            expires_at=now + REFRESH_TOKEN_LIFETIME_SECONDS,
        )

        self.access_tokens[access_token_str] = (access_token, user_email)
        self.refresh_tokens[refresh_token_str] = (refresh_token, user_email)

        return OAuthToken(
            access_token=access_token_str,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
            refresh_token=refresh_token_str,
            scope=" ".join(["mcp:tools"]),
        )

    # --- Access Token Verification ---

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Validate an MCP Bearer token."""
        entry = self.access_tokens.get(token)
        if not entry:
            return None
        access_token, _user_email = entry
        if access_token.expires_at and time.time() > access_token.expires_at:
            self.access_tokens.pop(token, None)
            return None
        return access_token

    # --- Refresh Token ---

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        """Look up an MCP refresh token."""
        entry = self.refresh_tokens.get(refresh_token)
        if not entry:
            return None
        rt, _user_email = entry
        if rt.expires_at and time.time() > rt.expires_at:
            self.refresh_tokens.pop(refresh_token, None)
            return None
        return rt

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Rotate MCP access + refresh tokens."""
        entry = self.refresh_tokens.pop(refresh_token.token, None)
        if not entry:
            raise TokenError(error="invalid_grant", error_description="Refresh token not found")
        _old_rt, user_email = entry

        now = int(time.time())
        new_access_str = secrets.token_urlsafe(32)
        new_refresh_str = secrets.token_urlsafe(32)

        new_access = AccessToken(
            token=new_access_str,
            client_id=client.client_id,
            scopes=["mcp:tools"],
            expires_at=now + ACCESS_TOKEN_LIFETIME_SECONDS,
        )
        new_refresh = RefreshToken(
            token=new_refresh_str,
            client_id=client.client_id,
            scopes=["mcp:tools"],
            expires_at=now + REFRESH_TOKEN_LIFETIME_SECONDS,
        )

        self.access_tokens[new_access_str] = (new_access, user_email)
        self.refresh_tokens[new_refresh_str] = (new_refresh, user_email)

        return OAuthToken(
            access_token=new_access_str,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
            refresh_token=new_refresh_str,
            scope=" ".join(["mcp:tools"]),
        )

    # --- Token Revocation ---

    async def revoke_token(
        self,
        client: OAuthClientInformationFull,
        token_type: str | None,
        token: str,
    ) -> None:
        """Revoke an MCP access or refresh token."""
        self.access_tokens.pop(token, None)
        self.refresh_tokens.pop(token, None)

    # --- Microsoft Graph Token Access (for tools) ---

    def get_user_email_for_token(self, mcp_token: str) -> str | None:
        """Get the user email associated with an MCP access token."""
        entry = self.access_tokens.get(mcp_token)
        if entry:
            _access_token, user_email = entry
            return user_email
        return None

    async def get_microsoft_token(self, user_email: str) -> str:
        """Get a valid Microsoft access token for Graph API calls.

        Uses MSAL's acquire_token_silent() which handles refresh automatically.
        """
        accounts = self._msal_app.get_accounts()
        target_account = None
        for account in accounts:
            if account.get("username", "").lower() == user_email.lower():
                target_account = account
                break

        if not target_account:
            raise RuntimeError(f"No cached Microsoft token for {user_email}")

        result = self._msal_app.acquire_token_silent(
            scopes=GRAPH_SCOPES,
            account=target_account,
        )

        if not result or "error" in result:
            raise RuntimeError(
                f"Failed to acquire Microsoft token: {result.get('error_description', 'unknown')}"
            )

        return result["access_token"]
