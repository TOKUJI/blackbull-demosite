"""BlackBull Demo — Live demonstration site for the BlackBull ASGI framework.

Single-file application entry point (target ≤300 lines).
Uses BlackBull's built-in server — no uvicorn, gunicorn, or hypercorn.

Launch methods::

    # Production (Alwaysdata — edge TLS, plain HTTP to app)
    blackbull blackbull_demo.app:app --bind :8000

    # Local dev (HTTP/1.1)
    python -m blackbull_demo.app
    BB_PORT=8080 python -m blackbull_demo.app

    # Local dev (HTTP/2 via self-signed cert — see scripts/gen-cert.sh)
    blackbull blackbull_demo.app:app --bind :8443 \\
        --certfile certs/cert.pem --keyfile certs/key.pem

Environment variables:

- ``BB_PORT`` — listening port (default 8000)
- ``BB_MAX_CONNECTIONS`` — per-worker connection cap (default 20)
- ``BB_WORKERS`` — worker processes (default 1; single worker required)
- ``BB_CERTFILE`` / ``BB_KEYFILE`` — TLS cert/key for local HTTP/2 dev only
  (production uses Alwaysdata edge TLS — no cert needed)

TLS strategy:
    - **Production:** Alwaysdata edge terminates TLS (Let's Encrypt).
      BlackBull receives plain HTTP/1.1 on localhost.
    - **Local dev:** Use ``scripts/gen-cert.sh`` to generate a self-signed
      cert and test BlackBull's built-in HTTP/2 + ALPN stack.
"""

from __future__ import annotations

import socket
import sys
import time
from collections import deque
from http import HTTPMethod, HTTPStatus
from importlib.metadata import version
from typing import Any

import blackbull
from blackbull import BlackBull, Event, JSONResponse, RedirectResponse, Response, read_text
from blackbull.middleware import Compression
from blackbull_htcpcp import HtcpcpExtension

from blackbull_demo.templates import render_dashboard

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_START_TIME: float = time.time()
_HOSTNAME: str = socket.gethostname()
_APP_VERSION: str = version('blackbull-demo')

# In-memory ring buffer for dashboard statistics (replaces stats.py).
_stats: dict[str, Any] = {'buf': deque(maxlen=50), 'total': 0}


# ===================================================================
# Application factory
# ===================================================================

def create_app() -> BlackBull:
    """Create and configure the BlackBull demo application.

    Returns a fully-wired ``BlackBull`` instance ready for ``app.run()``.
    """
    app = BlackBull()

    # -- Stats via built-in event system --------------------------------
    @app.on('request_completed')
    async def _record(event: Event):
        d = event.detail
        ua = _extract_user_agent(d.get('scope', {}))
        raw_status = d.get('status', 0)
        status = int(raw_status) if raw_status != '-' else 0
        _stats['buf'].append({
            'time': time.strftime('%H:%M:%S', time.gmtime()) + ' UTC',
            'method': d.get('method', '?'),
            'path': d.get('path', '/'),
            'status': status,
            'http_version': d.get('http_version', '1.1'),
            'elapsed_ms': round(d.get('duration_ms', 0.0), 2),
            'user_agent': ua[:60],
        })
        _stats['total'] += 1

    # -- Compression (dogfooding BlackBull's built-in middleware) ---------
    app.use(Compression())

    # -- Static files -----------------------------------------------------
    app.static('/static', 'static')

    # -- Legacy favicon redirect ------------------------------------------
    @app.route(path='/favicon.ico')
    async def favicon():
        """Redirect legacy /favicon.ico requests to the SVG favicon.

        Browsers that don't recognise ``<link rel="icon">`` with SVG
        fall back to requesting ``/favicon.ico`` from the origin root.
        """
        return RedirectResponse('/static/favicon.svg', status=HTTPStatus.MOVED_PERMANENTLY)

    # -- Routes -----------------------------------------------------------

    @app.route(path='/')
    async def dashboard(scope, receive, send):
        """HTML dashboard — human-facing landing page."""
        http_ver = _http_version_label(scope.get('http_version', '1.1'))
        routes = _get_route_list(app)
        html = render_dashboard(
            version=blackbull.__version__,
            hostname=_HOSTNAME,
            http_version=http_ver,
            routes=routes,
            stats=_build_stats_dict(),
        )
        await send(Response(html.encode(), content_type='text/html; charset=utf-8'))

    @app.route(path='/health')
    async def health():
        """Machine-readable JSON health check."""
        return {
            'status': 'ok',
            'version': blackbull.__version__,
            'app_version': _APP_VERSION,
            'uptime': round(time.time() - _START_TIME, 2),
            'hostname': _HOSTNAME,
        }

    @app.route(path='/stats.json')
    async def stats_json():
        """JSON export of in-memory statistics."""
        return _build_stats_dict()

    @app.route(path='/api/echo/{name}')
    async def echo(name: str):
        """Path-parameter routing demo."""
        return {'echo': name}

    @app.route(path='/api/square/{n:int}')
    async def square(n: int):
        """Type-coercion demo — ``int`` converter on ``{n:int}``."""
        return {'n': n, 'square': n * n}

    @app.route(path='/api/info')
    async def info():
        """Auto ``dict`` → ``JSONResponse`` demo."""
        return {
            'framework': 'BlackBull',
            'version': blackbull.__version__,
            'python': sys.version.split()[0],
        }

    @app.route(path='/api/headers')
    async def echo_headers(scope, receive, send):
        """httpbin-style request-header echo."""
        headers_out: dict[str, str] = {}
        for k, v in scope.get('headers', []):
            headers_out[k.decode('latin-1').lower()] = v.decode(
                'latin-1', errors='replace'
            )
        await send(JSONResponse({
            'method': scope.get('method', '?'),
            'path': scope.get('path', '/'),
            'http_version': scope.get('http_version', '1.1'),
            'headers': headers_out,
        }))

    @app.route(
        path='/api/methods',
        methods=[HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE],
    )
    async def methods_demo(scope, receive, send):
        """Method-based routing demo — one path, four HTTP methods."""
        method = scope.get('method', 'GET')
        body_preview = ''
        if method in ('POST', 'PUT'):
            body_text = await read_text(receive) or ''
            body_preview = body_text[:100]
        await send(JSONResponse({
            'method': method,
            'message': f'Handled {method} request',
            'body_preview': body_preview or None,
        }))

    # -- HTCPCP (RFC 2324) ------------------------------------------------
    HtcpcpExtension(app=app, pot_type='coffee')

    # -- OpenAPI / Swagger UI ---------------------------------------------
    # MUST be called *after* all route registrations.
    app.enable_openapi(
        title='BlackBull Demo',
        version=blackbull.__version__,
        description='Live demo of the BlackBull ASGI framework.',
    )

    # -- Error handlers ---------------------------------------------------
    @app.on_error(HTTPStatus.NOT_FOUND)
    async def _handle_404(scope, receive, send):
        await send(JSONResponse({'error': 'not found'}, status=HTTPStatus.NOT_FOUND))

    @app.on_error(Exception)
    async def _handle_500(scope, receive, send):
        await send(JSONResponse(
            {'error': 'internal server error'},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        ))

    return app


# ===================================================================
# Helpers
# ===================================================================

def _build_stats_dict() -> dict[str, Any]:
    """Build the statistics dict for dashboard / JSON export."""
    buf = _stats['buf']
    recent = list(reversed(buf))
    if buf:
        avg_ms = round(sum(r['elapsed_ms'] for r in buf) / len(buf), 2)
    else:
        avg_ms = 0.0
    return {
        'total_requests': _stats['total'],
        'avg_response_time_ms': avg_ms,
        'uptime_seconds': round(time.time() - _START_TIME, 2),
        'recent_requests': recent,
    }


def _extract_user_agent(scope: dict) -> str:
    """Extract User-Agent header from ASGI scope (first 60 chars)."""
    for k, v in scope.get('headers', []):
        if k.decode('latin-1').lower() == 'user-agent':
            return v.decode('utf-8', errors='replace')[:60]
    return ''

def _http_version_label(http_version: str) -> str:
    """Convert ASGI ``http_version`` to a human-readable label."""
    if http_version == '2':
        return 'HTTP/2 (h2)'
    return f'HTTP/{http_version}' if http_version else 'HTTP/1.1'


def _get_route_list(app: BlackBull) -> list[dict[str, str]]:
    """Extract registered route templates via ``app.get_routes()`` (public API)."""
    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ri in app.get_routes():
        key = (ri.method, ri.path)
        if key not in seen:
            seen.add(key)
            routes.append({'method': ri.method, 'path': ri.path, 'note': ''})

    # Annotate HTCPCP routes for dashboard clarity
    _htcpcp_notes = {
        ('BREW', '/pot'): 'HTCPCP BREW (RFC 2324)',
        ('PROPFIND', '/pot'): 'HTCPCP PROPFIND',
        ('WHEN', '/pot'): 'HTCPCP WHEN',
        ('POST', '/pot'): 'HTCPCP BREW (POST fallback)',
        ('GET', '/pot'): 'HTCPCP pot state',
        ('GET', '/pot/when'): 'HTCPCP when',
    }
    for r in routes:
        note = _htcpcp_notes.get((r['method'], r['path']))
        if note:
            r['note'] = note

    # Sort: static non-/pot → parameterised → /pot (HTCPCP last)
    def _sort_key(r: dict[str, str]) -> tuple[int, int, str, str]:
        is_pot = 1 if r['path'].startswith('/pot') else 0
        is_param = 1 if '{' in r['path'] else 0
        return (is_pot, is_param, r['path'], r['method'])
    routes.sort(key=_sort_key)
    return routes


# ===================================================================
# Module-level app (for CLI: blackbull blackbull_demo.app:app)
# ===================================================================

app = create_app()

# ===================================================================
# Entry point (python -m blackbull_demo.app / python app.py)
# ===================================================================

if __name__ == '__main__':
    # All BB_* env vars are resolved automatically by app.run().
    # max_connections=20 is enforced per Alwaysdata free-tier constraints.
    import subprocess
    from pathlib import Path

    _certfile = Path('certs/cert.pem')
    _keyfile = Path('certs/key.pem')
    if _certfile.exists() and _keyfile.exists():
        _bb_cli = str(Path(sys.executable).parent / 'blackbull')
        subprocess.Popen(
            [_bb_cli, 'blackbull_demo.app:app',
             '--bind', ':8443', '--certfile', str(_certfile), '--keyfile', str(_keyfile)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print('HTTPS (HTTP/2) → https://localhost:8443')
    print('HTTP (HTTP/1.1) → http://localhost:8000')
    create_app().run(port=8000, max_connections=20)
