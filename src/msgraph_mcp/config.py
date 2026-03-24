"""Configuration for msgraph-mcp server."""

import os

# Comma-separated list of allowed Microsoft account emails.
ALLOWED_USERS: list[str] = [
    email.strip().lower()
    for email in os.environ.get("MSGRAPH_MCP_ALLOWED_USERS", "lucas.augusto.meyer@outlook.com").split(",")
    if email.strip()
]


def is_user_allowed(email: str) -> bool:
    """Check whether a given email is in the allowed users list."""
    return email.strip().lower() in ALLOWED_USERS
