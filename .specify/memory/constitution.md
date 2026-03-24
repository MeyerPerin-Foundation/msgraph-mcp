<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0
- Modified principles: N/A (initial creation)
- Added sections: Core Principles (5), Security & Access Control, Development Workflow, Governance
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no update needed (Constitution Check section is generic)
  - .specify/templates/spec-template.md ✅ no update needed (structure compatible)
  - .specify/templates/tasks-template.md ✅ no update needed (phase structure compatible)
  - .github/copilot-instructions.md ✅ no update needed (PR auto-merge aligned with Principle V)
  - README.md ⚠ pending (still references src/ layout and FastAPI; separate cleanup)
- Follow-up TODOs: README.md update for current project structure
-->

# msgraph-mcp Constitution

## Core Principles

### I. Thin MCP Wrapper

Every MCP tool MUST map directly to one or more Microsoft Graph
REST API calls with minimal transformation. The server MUST NOT
invent domain logic beyond what Graph provides. Rationale: keeping
the wrapper thin ensures the server stays maintainable as the
Graph API evolves and avoids duplicating logic that belongs in the
Graph service itself.

### II. Consumer-Account Only

The server MUST target Microsoft personal accounts (MSA) exclusively.
Entra ID / work-or-school accounts are out of scope. OAuth flows,
token handling, and Graph API scopes MUST be configured for the
consumer endpoint (`https://graph.microsoft.com/v1.0`). Rationale:
a single-tenant focus simplifies auth, reduces configuration
surface, and matches the project's stated purpose.

### III. Secure by Default

OAuth 2.0 authorization code flow with PKCE MUST be used for
user authentication. Tokens MUST never be exposed to the AI
client or logged. Allowed users MUST be enforced via the
`config.py` allowlist. All traffic MUST use HTTPS. Secrets
MUST NOT be committed to source control. Rationale: the server
handles personal data (mail, calendar, files) and security
failures are unrecoverable trust violations.

### IV. Test Before Ship

All new MCP tools and configuration changes MUST have
corresponding tests. Tests MUST be runnable via `uv run pytest`.
CI MUST pass before merge. Rationale: the server runs as a
remote service; regressions directly break AI assistant
workflows with no manual fallback.

### V. Automated Deployment

Infrastructure MUST be defined in Bicep (`infra/main.bicep`).
Deployments MUST go through the GitHub Actions CI/CD pipeline.
Pull requests MUST use squash merge with auto-merge enabled
(`gh pr merge --squash --auto`). Direct pushes to `main` are
prohibited. Rationale: reproducible infrastructure and gated
deployments prevent configuration drift and broken production.

## Security & Access Control

- The `MSGRAPH_MCP_ALLOWED_USERS` environment variable controls
  which Microsoft accounts may use the server. Default: the
  project owner's account only.
- Graph API scopes MUST follow the principle of least privilege;
  request only the scopes each tool requires.
- No PII or tokens in logs. Structured logging MUST redact
  sensitive fields.

## Development Workflow

- **Package management**: uv (lockfile committed as `uv.lock`).
- **Project layout**: flat layout (`msgraph_mcp/` at repo root).
- **Server framework**: FastMCP with Starlette (no FastAPI).
- **Production runtime**: gunicorn with uvicorn workers on
  Azure App Service (Linux, Python 3.13).
- **Linting**: ruff.
- **Branching**: feature branches (`feat/`, `fix/`, `chore/`)
  off `main`. Never commit directly to `main`.
- **CI/CD**: GitHub Actions → `uv pip compile` → zip deploy →
  Azure App Service via `azure/webapps-deploy`.

## Governance

This constitution supersedes conflicting guidance in other
project documents. Amendments require:

1. A pull request modifying `.specify/memory/constitution.md`.
2. Version bump following semver (MAJOR for principle removal
   or redefinition, MINOR for new principles or sections,
   PATCH for clarifications).
3. Sync Impact Report updated in the HTML comment header.

All code reviews MUST verify compliance with these principles.
Complexity beyond what the principles allow MUST be justified
in the PR description.

**Version**: 1.0.0 | **Ratified**: 2026-03-24 | **Last Amended**: 2026-03-24
