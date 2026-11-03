# BlackBull Demo

[![Health Check](https://img.shields.io/badge/demo-live-brightgreen)](https://blackbull.alwaysdata.net/health)
[![BlackBull](https://img.shields.io/badge/powered_by-BlackBull-orange)](https://pypi.org/project/blackbull/)

Live demonstration site for the [BlackBull web framework](https://pypi.org/project/blackbull/) — native typed `Connection` end to end, ASGI 3.0 as an interop boundary.

## What This Is

A permanently-running live demo proving that BlackBull runs in production
on a real (free) cloud host, serving real traffic, with **no external server
dependencies** — no uvicorn, no gunicorn, no hypercorn.

## Live Demo

- **Dashboard:** [https://blackbull.alwaysdata.net/](https://blackbull.alwaysdata.net/)
- **Health Check:** [https://blackbull.alwaysdata.net/health](https://blackbull.alwaysdata.net/health)
- **Swagger UI:** [https://blackbull.alwaysdata.net/docs](https://blackbull.alwaysdata.net/docs)
- **OpenAPI Spec:** [https://blackbull.alwaysdata.net/openapi.json](https://blackbull.alwaysdata.net/openapi.json)

## Features Demonstrated

| Feature | Endpoint |
|---|---|
| Path parameter routing | `GET /api/echo/{name}` |
| Type coercion (`int` converter) | `GET /api/square/{n:int}` |
| Auto `dict` → `JSONResponse` | `GET /api/info` |
| Request header echo | `GET /api/headers` |
| Method-based routing | `GET/POST/PUT/DELETE /api/methods` |
| HTTP QUERY method (RFC 10008) | `QUERY /api/changelog` |
| Health & stats JSON export | `GET /health`, `GET /stats.json` |
| Built-in OpenAPI + Swagger UI | `GET /openapi.json`, `GET /docs` |
| HTTP cache validators (ETag → `304`) | `GET /robots.txt`, `GET /sitemap.xml` |
| HTCPCP (RFC 2324 Coffee Pot) | `POST /pot`, `GET /pot`, `GET /pot/when` |

## Running Locally

```bash
# Clone and install
git clone https://github.com/TOKUJI/blackbull-demosite.git
cd blackbull-demosite
pip install -e .

# Run (BlackBull has its own built-in server — no uvicorn needed)
python -m blackbull_demo.app

# Open http://localhost:8000
```

## Hosting

Hosted on [Alwaysdata](https://www.alwaysdata.com/) free tier:
- 256 MB RAM, 1 GB SSD, ¼ CPU
- Always-on (no sleep), no credit card required
- **Services** (24/7 process supervisor) + **Apache reverse proxy**
- Edge TLS termination with automatic Let's Encrypt

Architecture:
```
Internet → :443 (TLS) → Apache (ProxyPass) → Service :8300 → BlackBull
```

## License

MIT — see [LICENSE](./LICENSE).
