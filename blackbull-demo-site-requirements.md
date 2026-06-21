# BlackBull Demo Site — Requirements Definition

**Status:** Draft  
**Date:** 2026-06-21  
**Purpose:** Define what the BlackBull live demo site shows, how it is built, where it is hosted, and what risks are addressed before public launch.

---

## 1. Purpose

A permanently-running live demo of the BlackBull ASGI framework, linked from:

- The BlackBull `README.md` (badge + link)
- Dev.to articles and other promotional material
- The BlackBull documentation site

The demo serves as **proof of life** — that BlackBull runs in production on a real (free) cloud host, serving real traffic, without external server dependencies.

---

## 2. Hosting

### 2.1 Selected Provider: Alwaysdata

| Criterion | Alwaysdata |
|---|---|
| Free tier | ✅ 0€ for life — 1 GB SSD, 256 MB RAM, ¼ CPU |
| Credit card required | ❌ Not required |
| Python ASGI | ✅ Run uvicorn/any Python process via SSH daemon |
| Sleep on idle | ✅ **No sleep** — always-on traditional hosting |
| Custom domains | ✅ Supported (free email included) |
| Time limit | ✅ None — "for life" |

### 2.2 Rationale

Alwaysdata is the only service combining all four critical requirements:
no credit card, Python support, always-on (no sleep), and custom domains.

The 256 MB RAM constraint is acceptable: BlackBull runs its own built-in server
(no uvicorn overhead), uses no database, and serves a single worker with
`max_connections` capped at ~20.

### 2.3 Keep-Warm / Monitoring

- **UptimeRobot** (free tier): HTTP monitor polling `GET /health` every 5 minutes
- **Alwaysdata daemon**: auto-restart on process exit
- **GitHub Actions cron** (optional): secondary health check every hour

### 2.4 Alternatives Considered

| Service | Verdict | Reason |
|---|---|---|
| Render | 🥈 Backup | 512 MB RAM but 15-min idle sleep; workaround with ping |
| PythonAnywhere | ❌ | 100 CPU-seconds/day limit; no custom domains on free; ASGI is beta |
| Oracle Cloud | ❌ | Credit card required; idle instance reclamation kills low-traffic sites |
| Northflank | ❌ | Credit card required despite free tier |
| Railway | ❌ | $5/mo after trial; not permanently free |
| Fly.io | ❌ | No permanent free tier (7-day trial only) |
| Koyeb | ❌ | No free compute tier |

---

## 3. Repository

### 3.1 Decision: Separate Git Repository

**Repository:** `github.com/TOKUJI/blackbull-demo` (or similar)

### 3.2 Rationale for Separate Repo

| Factor | Separate Repo | In `examples/demo_site/` |
|---|---|---|
| Deployment | ✅ Clone only demo (~KB) | ❌ Clone full BlackBull (~MB) |
| Dependencies | ✅ `pip install blackbull blackbull-htcpcp` | ❌ Editable install or relative path |
| "External consumer" feel | ✅ Natural | ❌ Feels like internal code |
| Discoverability | 🟡 Needs README badge | ✅ In `examples/` |
| Versioning | 🟡 Explicit dep pinning needed | ✅ Always in sync |

The demo site is a **consumer** of BlackBull, not a framework component.
It should demonstrate real-world usage: `pip install blackbull`, write `app.py`, deploy.

### 3.3 Repository Structure

```
blackbull-demo/
├── README.md          # "This site runs on BlackBull" + link to live demo
├── pyproject.toml     # deps: blackbull, blackbull-htcpcp
├── app.py             # main application (~250 lines target)
├── templates.py       # inline HTML templates (no external CSS/JS)
└── stats.py           # ring-buffer request statistics
```

---

## 4. What the Demo Shows

### 4.1 Core — Proof of Life

| Endpoint | Method | Content |
|---|---|---|
| `/` | GET | Human-facing HTML dashboard |
| `/health` | GET | Machine-readable JSON: `{"status":"ok","version":"...","uptime":...}` |
| `/stats.json` | GET | Machine-readable JSON export of statistics |

### 4.2 Framework Feature Demos

| Endpoint | Method | Demonstrated Feature |
|---|---|---|
| `/api/echo/{name}` | GET | Path parameter routing |
| `/api/square/{n:int}` | GET | Type coercion (`int` converter) |
| `/api/info` | GET | Automatic `dict` → `JSONResponse` |
| `/api/headers` | GET | httpbin-style request header echo |
| `/api/methods` | GET/POST/PUT/DELETE | Method-based routing |

### 4.3 OpenAPI / Swagger UI

```python
app.enable_openapi(
    title='BlackBull Demo',
    version=blackbull.__version__,
    description='Live demo of the BlackBull ASGI framework.',
)
```

Publishes:
- `GET /openapi.json` — OpenAPI 3.1 JSON spec (auto-generated from routes)
- `GET /docs` — Swagger UI (loaded from CDN, no static files)

Rationale: demonstrates BlackBull's built-in OpenAPI support; zero additional dependencies;
adds "production-grade framework" credibility.

### 4.4 HTCPCP (RFC 2324 Easter Egg)

```python
from blackbull_htcpcp import HtcpcpExtension
HtcpcpExtension(app=app, pot_type='coffee')
```

Publishes:
- `POST /pot` — BREW (coffee brewing with `Accept-Additions` header)
- `GET /pot` — Current pot state
- `GET /pot/when` — Brew readiness check
- `418 I'm a teapot` — Proper RFC 2324 §2.2.2 response when teapot mode

Rationale:
- Humor — recognizable tech inside joke
- Demonstrates BlackBull's extension system (`init_app(app)` convention)
- Demonstrates non-standard HTTP (418 status, BREW method, `message/coffeepot` MIME type)
- Shows defensive input validation (body caps, token limits, CRLF/NULL rejection)

### 4.5 Dashboard Page (`/`) Content

```
┌──────────────────────────────────────────────────┐
│  🐂 BlackBull Demo                                │
│  Running BlackBull vX.Y.Z on Python 3.X           │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Status   │ │ Protocol │ │ Uptime           │  │
│  │ ● ONLINE │ │ HTTP/2   │ │ 3d 12h 45m       │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
│                                                   │
│  Your Connection                                  │
│  Protocol:    HTTP/2 (h2)                         │
│  Encryption:  TLS 1.3                             │
│  Method:      GET                                 │
│                                                   │
│  📋 Registered Routes (N routes)                  │
│  GET  /                                           │
│  GET  /health                                     │
│  GET  /openapi.json                               │
│  GET  /docs                                       │
│  GET  /api/echo/{name}                            │
│  GET  /api/square/{n:int}                         │
│  POST /pot           (HTCPCP BREW)                │
│  ...                                              │
│                                                   │
│  📡 Recent Requests (last 50)                     │
│  [12:34:56] GET / 200 HTTP/2 0.2ms               │
│  [12:34:50] GET /health 200 HTTP/1.1 0.1ms       │
│  ...                                              │
│                                                   │
│  📊 Statistics                                    │
│  Total Requests:    12,345                        │
│  Active Connections: 3                            │
│  Avg Response Time:  1.2ms                        │
│                                                   │
│  🔗 GitHub · Docs · PyPI                          │
│  Powered by BlackBull — no uvicorn, no gunicorn   │
└──────────────────────────────────────────────────┘
```

---

## 5. How the Demo Looks

### 5.1 Design Principles

- **Zero external CSS/JS** — all styles inlined; no Tailwind, no Bootstrap, no CDN
- **Dark mode** via `prefers-color-scheme` media query (a few lines of CSS)
- **HAProxy-inspired transparency** — real statistics tables, not marketing fluff
- **Caddy-inspired terminal aesthetic** — dark background, monospace stats, clean layout
- **Response size target:** < 10 KB for the HTML dashboard

### 5.2 Information Display Rules

| Show | Do NOT Show |
|---|---|
| BlackBull version (`__version__`) | Python minor/patch version detail |
| Hostname (`socket.gethostname()`) | Server internal IP address |
| Startup time (UTC) | Server local timezone |
| Registered route templates | Route handler source code |
| Recent request method + path | Full request headers or body |
| User-Agent (first 60 chars) | Client IP address |
| Client's HTTP protocol version | — |

### 5.3 Protocol Display

Detect and display the client's connection protocol via `scope['http_version']`:

| `scope['http_version']` | Display |
|---|---|
| `"2"` | `HTTP/2 (h2)` |
| `"1.1"` | `HTTP/1.1` |

For future non-HTTP protocols (MQTT, Redis, raw TCP), the display is a deferred concern:
these protocols do not use HTTP URLs and their connections are dispatched via
`ProtocolRegistry` / `ProtocolDetector`, not the ASGI router. The demo's focus
is HTTP for the initial release; non-HTTP protocol status can be added when
BlackBull's multi-protocol story matures.

---

## 6. Threat Model & Mitigations

### 6.1 Resource Exhaustion (Primary Concern — 256 MB RAM)

| Threat | Risk | Mitigation |
|---|---|---|
| High request volume (mini DDoS) | OOM kill | `max_connections` ≤ 20; single worker |
| Slowloris | Exhausted connection pool | Short keep-alive timeout (~5 s); connection deadline |
| Large request body | Memory buffer OOM | Body size cap (~1 MB); `/api/*` routes don't read body |
| WebSocket connection hoarding | Open connections consume memory | **No WebSocket endpoints in the demo** |
| Log file growth | Disk exhaustion (1 GB SSD) | Ring-buffer in-memory stats only; no file logging |
| HN/Reddit hug of death | 256 MB cannot survive | **Accept the limit.** The demo breaking under load is itself data about BlackBull's resource profile |

### 6.2 Information Leakage

| Threat | Mitigation |
|---|---|
| Traceback in response body | Global error handler returns generic message; `debug=False` |
| `Server` header leaking version | Suppress or emit only `BlackBull` (no version) |
| Stack trace exposure | Catch-all exception handler; never return tracebacks |
| Path enumeration | Only registered route templates are shown; internal paths not guessable |

### 6.3 Abuse / Pivoting

| Threat | Mitigation |
|---|---|
| SSRF via demo features | No endpoints that fetch external URLs |
| Open redirect | No redirect functionality in demo endpoints |
| Reverse proxy spoofing | Do not trust `X-Forwarded-For`; verify Alwaysdata's actual proxy configuration |

### 6.4 Availability

| Threat | Mitigation |
|---|---|
| Process crash / OOM kill | Alwaysdata daemon auto-restart |
| Alwaysdata platform outage | UptimeRobot alerting; accept as platform SLA |
| DNS / domain expiry | Monitor separately |

---

## 7. Dependencies

### 7.1 Runtime

```
blackbull               # The framework itself (includes built-in server)
blackbull-htcpcp         # HTCPCP extension (RFC 2324 easter egg)
```

**Explicitly NOT included:**
- `uvicorn` / `hypercorn` / `granian` — BlackBull is its own server
- `jinja2` — inline Python string templates
- Any database driver — in-memory `collections.deque` ring buffer
- Any CSS/JS framework — inline styles only
- `pydantic` / `msgspec` — not needed for this demo

### 7.2 Development / Testing

```
pytest
pytest-asyncio
blackbull[testing]
```

---

## 8. Deployment

### 8.1 Alwaysdata Setup

```bash
# SSH into Alwaysdata
ssh <user>@ssh-<user>.alwaysdata.net

# Clone the demo
git clone https://github.com/TOKUJI/blackbull-demo.git
cd blackbull-demo

# Create virtualenv and install
python3 -m venv .venv
.venv/bin/pip install blackbull blackbull-htcpcp

# Configure daemon (via Alwaysdata admin panel or SSH)
# Command: /home/<user>/blackbull-demo/.venv/bin/python /home/<user>/blackbull-demo/app.py
# Environment: BB_PORT=8000
```

### 8.2 Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `BB_PORT` | `8000` | Listening port |
| `BB_MAX_CONNECTIONS` | `20` | Hard cap on concurrent connections |
| `BB_WORKERS` | `1` | Single worker (required when raw_handler present, memory-optimal) |

---

## 9. Non-Goals (Explicitly Out of Scope for v1)

- ❌ WebSocket demo endpoints
- ❌ User-specific state or sessions
- ❌ Database / persistence of any kind
- ❌ Authentication / authorization
- ❌ Rate limiting middleware (defer to `max_connections` cap)
- ❌ Non-HTTP protocol status display (MQTT, Redis — deferred to future)
- ❌ Multi-language support
- ❌ Analytics / tracking
- ❌ TLS (Alwaysdata provides HTTPS termination at their edge)
- ❌ Docker / container deployment

---

## 10. Success Criteria

1. The site is reachable 24/7 at its public URL
2. `GET /health` returns `200 OK` with valid JSON including version and uptime
3. The dashboard at `/` correctly shows the client's HTTP protocol version
4. `GET /docs` renders Swagger UI with all demo routes documented
5. `POST /pot` with `Accept-Additions: cream; sugar` returns `200` with coffee pot state
6. `GET /pot` on a teapot-configured instance returns `418 I'm a teapot`
7. The site survives moderate traffic without OOM (validated by `max_connections` cap)
8. UptimeRobot reports ≥ 99.5% uptime (allowing for Alwaysdata platform maintenance)
9. README of `blackbull` repo links to the live demo with a status badge
10. The entire demo fits in a single `app.py` under 300 lines (plus `templates.py` and `stats.py`)

---

## 11. References

- [Alwaysdata Free Tier](https://www.alwaysdata.com/)
- [blackbull-htcpcp on PyPI](https://pypi.org/project/blackbull-htcpcp/)
- [BlackBull OpenAPI Documentation](https://github.com/TOKUJI/BlackBull/blob/master/docs/guide/openapi.md)
- [BlackBull Extensions Guide](https://github.com/TOKUJI/BlackBull/blob/master/docs/guide/extensions.md)
- [RFC 2324 — Hyper Text Coffee Pot Control Protocol](https://datatracker.ietf.org/doc/html/rfc2324)
- [RFC 7168 — HTCPCP-TEA](https://datatracker.ietf.org/doc/html/rfc7168)
- [HAProxy Live Demo](http://demo.haproxy.org/) — inspiration for transparency/statistics display
- [Caddy Web Server](https://caddyserver.com/) — inspiration for interactive demo presentation
