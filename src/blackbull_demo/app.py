"""BlackBull Demo — Live demonstration site for the BlackBull ASGI framework.

Single-file application entry point (target ≤300 lines).
Uses BlackBull's built-in server — no uvicorn, gunicorn, or hypercorn.

See `blackbull run --help` and the BlackBull deployment guide for
environment variables (`BLACKBULL_PORT`, `BLACKBULL_MAX_CONNECTIONS`, etc.).

TLS strategy:
    - **Production:** Alwaysdata edge terminates TLS (Let's Encrypt).
      Apache reverse-proxies to the Service on ``[::]:8300``.
      BlackBull receives plain HTTP/1.1 on the Services server.
    - **Local dev:** Use ``scripts/gen-cert.sh`` to generate a self-signed
      cert and test BlackBull's built-in HTTP/2 + ALPN stack.
"""

from __future__ import annotations

import json
import socket
import sys
import time
from collections import deque
from http import HTTPMethod, HTTPStatus
from importlib.metadata import version
from pathlib import Path
from typing import Any

import blackbull
from blackbull import (BlackBull, Connection, Event, JSONResponse, QUERY,
                       RedirectResponse, Response)
from blackbull.middleware import Compression
from blackbull_htcpcp import HtcpcpExtension, HtcpcpMethod

from blackbull_demo.templates import render_dashboard

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_START_TIME: float = time.time()
_HOSTNAME: str = socket.gethostname()
_APP_VERSION: str = version('blackbull-demo')

# In-memory ring buffer for dashboard statistics (replaces stats.py).
_stats: dict[str, Any] = {'buf': deque(maxlen=50), 'total': 0}

# BlackBull changelog data (loaded once at import time).
_CHANGELOG_PATH = Path(__file__).parent / 'changelog.json'
with open(_CHANGELOG_PATH) as _f:
    _CHANGELOG: dict[str, dict] = json.load(_f)

# sitemap.xml template (loaded once at import time).
_SITEMAP_PATH = Path(__file__).parent / 'sitemap.xml'
with open(_SITEMAP_PATH) as _f:
    _SITEMAP_TEMPLATE: str = _f.read()


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
        _stats['buf'].append({
            'time': time.strftime('%H:%M:%S', time.gmtime()) + ' UTC',
            'method': d.get('method', '?'),
            'path': d.get('path', '/'),
            'status': _coerce_status(d.get('status', 0)),
            'http_version': d.get('http_version', '1.1'),
            'elapsed_ms': round(float(d.get('duration_ms', 0.0)), 2),
            'bytes': int(d.get('response_bytes', 0) or 0),
            'user_agent': _extract_user_agent(d.get('scope', {}))[:60],
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

    # -- robots.txt -------------------------------------------------------
    @app.route(path='/robots.txt')
    async def robots_txt(conn: Connection):
        """Serve robots.txt with Sitemap directive."""
        host = _get_host(conn)
        body = (
            'User-agent: *\n'
            'Disallow: /static/\n'
            'Disallow: /api/\n'
            'Allow: /\n'
            f'Sitemap: https://{host}/sitemap.xml\n'
        )
        return Response(body.encode(), content_type='text/plain')

    # -- Routes -----------------------------------------------------------

    @app.route(path='/')
    async def dashboard(conn: Connection):
        """HTML dashboard — human-facing landing page."""
        http_ver = _http_version_label(conn.http_version)
        routes = _get_route_list(app)
        html = render_dashboard(
            version=blackbull.__version__,
            hostname=_HOSTNAME,
            http_version=http_ver,
            routes=routes,
            stats=_build_stats_dict(),
        )
        return Response(html.encode(), content_type='text/html; charset=utf-8')

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
    async def echo_headers(conn: Connection):
        """httpbin-style request-header echo."""
        return {
            'method': conn.method,
            'path': conn.path,
            'headers': {k.decode('latin-1').lower(): v.decode('latin-1', errors='replace')
                        for k, v in conn.headers},
        }

    @app.route(
        path='/api/methods',
        methods=[HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE],
    )
    async def methods_demo(conn: Connection):
        """Method-based routing demo — one path, four HTTP methods."""
        body_preview = ''
        if conn.method in ('POST', 'PUT'):
            body_text = await conn.text() or ''
            body_preview = body_text[:100]
        return {
            'method': conn.method,
            'message': f'Handled {conn.method} request',
            'body_preview': body_preview or None,
        }

    # -- QUERY method demo (RFC 9110) ------------------------------------
    @app.route(path='/api/changelog', methods=[QUERY])
    async def query_changelog(conn: Connection):
        """QUERY method demo — search BlackBull changelog by version.

        Send a JSON body with ``{"version": "0.59.0"}`` to retrieve
        the changelog entry for that version.  An empty body or
        missing ``version`` key returns the list of available versions.
        """
        try:
            body = await conn.json() or {}
            return {'version': body['version'],
                    'changelog': _CHANGELOG[body['version']]}
        except KeyError:
            return {'available_versions': sorted(_CHANGELOG.keys(), reverse=True)}

    # -- Sitemap -----------------------------------------------------------
    @app.route(path='/sitemap.xml')
    async def sitemap_xml(conn: Connection):
        """Serve sitemap.xml — template with dynamic base URL."""
        host = _get_host(conn)
        body = _SITEMAP_TEMPLATE.replace('{base}', f'https://{host}')
        return Response(
            body.encode(), content_type='application/xml; charset=utf-8',
        )

    # -- HTCPCP (RFC 2324 + RFC 7168) ------------------------------------
    HtcpcpExtension(app=app, pot_type='coffee')                     # /pot
    HtcpcpExtension(app=app, pot_type='teapot', path='/teapot')     # /teapot

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


def _coerce_status(raw: object) -> int:
    """Coerce a status value from the event detail to int.

    The ``request_completed`` event may carry ``'-'`` as a placeholder
    when a global middleware buffers the response (BlackBull #145).
    """
    if raw == '-' or raw is None:
        return 0
    return int(raw)


def _get_host(conn: Connection) -> str:
    """Extract the public-facing hostname from connection headers.

    Prefers ``X-Forwarded-Host`` (set by reverse proxy) over ``Host``
    (which carries the internal backend address behind a proxy).
    """
    host = ''
    for k, v in conn.headers:
        key = k.decode('latin-1').lower()
        if key == 'x-forwarded-host':
            return v.decode('latin-1', errors='replace')
        if key == 'host':
            host = v.decode('latin-1', errors='replace')
    return host or 'localhost'


def _get_route_list(app: BlackBull) -> list[dict[str, str]]:
    """Extract registered route templates via ``app.get_routes()`` (public API)."""
    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ri in app.get_routes():
        key = (ri.method, ri.path)
        if key not in seen:
            seen.add(key)
            routes.append({'method': ri.method, 'path': ri.path, 'note': ''})

    # Annotate QUERY and HTCPCP routes for dashboard clarity
    _query_notes = {
        (QUERY, '/api/changelog'): 'QUERY method demo (RFC 9110)',
    }
    _htcpcp_notes = {
        # /pot — coffee (RFC 2324)
        (HtcpcpMethod.BREW, '/pot'):     'HTCPCP BREW (RFC 2324)',
        (HtcpcpMethod.PROPFIND, '/pot'): 'HTCPCP PROPFIND',
        (HtcpcpMethod.WHEN, '/pot'):     'HTCPCP WHEN',
        (HTTPMethod.POST, '/pot'):       'HTCPCP BREW (POST fallback)',
        (HTTPMethod.GET, '/pot'):        'HTCPCP pot state',
        (HTTPMethod.GET, '/pot/when'):   'HTCPCP when',
        # /teapot — tea (RFC 7168)
        (HtcpcpMethod.BREW, '/teapot'):     'HTCPCP-TEA BREW (RFC 7168)',
        (HtcpcpMethod.PROPFIND, '/teapot'): 'HTCPCP-TEA PROPFIND',
        (HtcpcpMethod.WHEN, '/teapot'):     'HTCPCP-TEA WHEN',
        (HTTPMethod.POST, '/teapot'):       'HTCPCP-TEA BREW (POST fallback)',
        (HTTPMethod.GET, '/teapot'):        'HTCPCP-TEA pot state',
        (HTTPMethod.GET, '/teapot/when'):   'HTCPCP-TEA when',
    }
    for r in routes:
        note = _query_notes.get((r['method'], r['path'])) or \
               _htcpcp_notes.get((r['method'], r['path']))
        if note:
            r['note'] = note

    # Sort: static → parameterised → /pot → /teapot (HTCPCP last)
    def _sort_key(r: dict[str, str]) -> tuple[int, int, str, str]:
        is_htcpcp = (
            2 if r['path'].startswith('/teapot') else
            1 if r['path'].startswith('/pot') else
            0
        )
        is_param = 1 if '{' in r['path'] else 0
        return (is_htcpcp, is_param, r['path'], r['method'])
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
