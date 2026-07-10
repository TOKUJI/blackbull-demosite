# BlackBull Demo — Copilot Instructions

This file provides always-on coding constraints and conventions for the
`blackbull-demo` repository. Copilot MUST follow these rules for every
code generation, edit, or suggestion in this project.

---

## Core Architecture

- **Framework:** BlackBull ASGI (imported as `blackbull`)
- **Server:** BlackBull's built-in server ONLY (`app.run()`). NEVER import or
  suggest `uvicorn`, `hypercorn`, `granian`, `gunicorn`, or any other ASGI server.
- **Production deployment:** Alwaysdata **Services** (24/7 supervisor) on
  port 8300, with Apache **reverse proxy** (ProxyPass) from edge TLS :443.
  See `scripts/run-service.sh` and `scripts/deploy.sh`.
- **Route registration:** `app.route()` (decorator) — NOT `add_route()`.
- **Application entry point:** `app.py` — single file, target ≤300 lines.
- **Template strings:** `templates.py` — inline HTML as Python string
  constants. NEVER import `jinja2` or any template engine.
- **Statistics:** `stats.py` — `collections.deque` ring buffer.
  NEVER import any database driver.

---

## Dependency Rules (STRICT)

### ALLOWED runtime dependencies:
- `blackbull`
- `blackbull-htcpcp`

### FORBIDDEN dependencies (do NOT import, suggest, or add):
- `uvicorn`, `hypercorn`, `granian` — BlackBull is its own server
- `jinja2` — use inline Python f-strings / `str.format()` only
- Any database driver (`sqlite3`, `sqlalchemy`, `asyncpg`, etc.)
- `pydantic`, `msgspec` — not needed for this demo
- Any CSS framework (`tailwindcss`, `bootstrap`, etc.)
- Any JavaScript framework or library
- Any external CDN resource (except Swagger UI assets loaded by
  BlackBull's built-in `enable_openapi()`)

---

## HTML / CSS Rules

- ALL CSS must be inlined in `<style>` tags within the HTML string.
- NO external `.css` files. NO CDN stylesheets.
- Dark mode via `prefers-color-scheme: dark` media query only.
- Design aesthetic: **HAProxy-inspired transparency** + **Caddy-inspired
  terminal look** — dark background, monospace stats, clean layout.
- Response size target: **< 10 KB** for the HTML dashboard (`GET /`).
- Use `<meta>` viewport for mobile-friendly display.

---

## Resource Constraints (Alwaysdata Free Tier)

| Constraint | Value |
|---|---|
| RAM | 256 MB |
| Disk | 1 GB SSD |
| `max_connections` | ≤ 20 |
| Workers | 1 (single worker) |
| Body size cap | ~1 MB |

- NEVER create WebSocket endpoints (connections consume memory).
- NEVER write to log files — use in-memory ring buffer only.
- Keep-alive timeout should be short (~5 seconds).

---

## Information Security

- NEVER expose tracebacks in HTTP responses.
- NEVER expose internal IP addresses, server paths, or environment variables.
- `Server` header: emit `BlackBull` only (no version).
- Global error handler must return generic messages (`debug=False`).
- Show `User-Agent` (first 60 chars) but NEVER client IP address.
- Show hostname (`socket.gethostname()`) but NEVER server internal IP.

---

## Endpoint Inventory

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | HTML dashboard |
| `/health` | GET | JSON health check (`status`, `version`, `uptime`) |
| `/stats.json` | GET | JSON statistics export |
| `/api/echo/{name}` | GET | Path parameter routing demo |
| `/api/square/{n:int}` | GET | Type coercion demo |
| `/api/info` | GET | Auto dict→JSONResponse demo |
| `/api/headers` | GET | Request header echo (httpbin-style) |
| `/api/methods` | GET/POST/PUT/DELETE | Method-based routing demo |
| `/openapi.json` | GET | Auto-generated OpenAPI 3.1 spec |
| `/docs` | GET | Swagger UI |
| `/pot` | POST/GET | HTCPCP (RFC 2324) coffee pot |
| `/pot/when` | GET | HTCPCP brew readiness check |

---

## HTCPCP (RFC 2324) Rules

- Use `blackbull_htcpcp.HtcpcpExtension` with `pot_type='coffee'`.
- `POST /pot` with `Accept-Additions` header → BREW.
- `GET /pot` on teapot-configured instance → `418 I'm a teapot`.
- Defensive input validation: body caps, token limits, CRLF/NULL rejection.

---

## OpenAPI

```python
app.enable_openapi(
    title='BlackBull Demo',
    version=blackbull.__version__,
    description='Live demo of the BlackBull ASGI framework.',
)
```

No additional dependencies — this is built into BlackBull.

---

## Testing

- Framework: `pytest` + `pytest-asyncio`
- `asyncio_mode = "auto"` (set in `pyproject.toml`)
- Test files: `tests/test_app.py` (integration), `tests/test_stats.py` (unit)
- Fixtures in `tests/conftest.py`

---

## Git / GitHub Workflow

- **Branch strategy:**
  - `main` — deployable production (Alwaysdata clones this)
  - `develop` — integration branch for PRs
  - `feature/<name>` — feature branches
- **Pull Requests:** `feature/*` → `develop`, Squash & Merge only.
- **Commit messages:** Conventional Commits format
  (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- **CI:** `.github/workflows/health-check.yml` runs hourly health check
  against the live demo URL.
- **Deploy:** `scripts/deploy.sh` handles SSH-based deployment to Alwaysdata.
