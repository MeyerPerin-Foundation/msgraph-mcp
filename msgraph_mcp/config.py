"""Configuration for msgraph-mcp server."""

import os
from pathlib import Path

# Comma-separated list of allowed Microsoft account emails.
ALLOWED_USERS: list[str] = [
    email.strip().lower()
    for email in os.environ.get("MSGRAPH_MCP_ALLOWED_USERS", "lucas.augusto.meyer@outlook.com").split(",")
    if email.strip()
]


def is_user_allowed(email: str) -> bool:
    """Check whether a given email is in the allowed users list."""
    return email.strip().lower() in ALLOWED_USERS


# OAuth configuration — loaded from environment variables.
MSGRAPH_CLIENT_ID: str = os.environ.get("MSGRAPH_CLIENT_ID", "")
MSGRAPH_CLIENT_SECRET: str = os.environ.get("MSGRAPH_CLIENT_SECRET", "")
MSGRAPH_REDIRECT_URI: str = os.environ.get(
    "MSGRAPH_REDIRECT_URI", "http://localhost:8000/auth/microsoft/callback"
)
MSGRAPH_SERVER_URL: str = os.environ.get(
    "MSGRAPH_SERVER_URL", "http://localhost:8000"
)

# MCP OAuth scopes exposed by this server.
MCP_REQUIRED_SCOPES: list[str] = ["mcp:tools"]

MICROSOFT_AUTHORITY = "https://login.microsoftonline.com/consumers"
GRAPH_SCOPES: list[str] = [
    "User.Read",
    "Mail.ReadWrite",
    "Mail.Send",
    "Calendars.ReadWrite",
    "Tasks.ReadWrite",
    "Files.Read",
]

# Credential cache directory — override with MSGRAPH_CACHE_DIR env var.
MSGRAPH_CACHE_DIR: Path = Path(
    os.environ.get("MSGRAPH_CACHE_DIR", ".local/cache")
)
