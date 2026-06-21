"""BlackBull Demo — Live demonstration site for the BlackBull ASGI framework.

Single-file application entry point (target ≤300 lines).
Uses BlackBull's built-in server — no uvicorn, gunicorn, or hypercorn.

Usage::

    python -m blackbull_demo               # default port 8000
    BB_PORT=8080 python -m blackbull_demo  # custom port
    BB_MAX_CONNECTIONS=10 python -m blackbull_demo  # lower connection cap

Environment variables:

- ``BB_PORT`` — listening port (default 8000)
- ``BB_MAX_CONNECTIONS`` — per-worker connection cap (default 20)
- ``BB_WORKERS`` — worker processes (default 1; single worker required)
"""

from __future__ import annotations

import os
import socket
import sys
import time
from http import HTTPMethod, HTTPStatus

import blackbull
from blackbull import BlackBull, JSONResponse, Response
from blackbull_htcpcp import HtcpcpExtension

from blackbull_demo.stats import stats
from blackbull_demo.templates import render_dashboard

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_START_TIME: float = time.time()
_HOSTNAME: str = socket.gethostname()


# ===================================================================
# Application factory
# ===================================================================

def create_app() -> BlackBull:
    """Create and configure the BlackBull demo application.

    Returns a fully-wired ``BlackBull`` instance ready for ``app.run()``.
    """
    app = BlackBull()

    # -- Global middleware ------------------------------------------------
    app.use(_stats_middleware)

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
            stats=stats.to_dict(),
        )
        await send(Response(html.encode(), content_type='text/html; charset=utf-8'))

    @app.route(path='/health')
    async def health():
        """Machine-readable JSON health check."""
        return {
            'status': 'ok',
            'version': blackbull.__version__,
            'uptime': round(time.time() - _START_TIME, 2),
            'hostname': _HOSTNAME,
        }

    @app.route(path='/stats.json')
    async def stats_json():
        """JSON export of in-memory statistics."""
        return stats.to_dict()

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
            msg = await receive()
            if msg['type'] == 'http.request':
                body = msg.get('body', b'')
                body_preview = body.decode('utf-8', errors='replace')[:100]
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
# Middleware
# ===================================================================

async def _stats_middleware(scope, receive, send, call_next):
    """Record timing and status for every HTTP request."""
    stats.inc_connections()
    start_ts = time.monotonic()
    response_status: list[int] = [200]

    async def _capture_send(msg):
        if msg['type'] == 'http.response.start':
            response_status[0] = msg['status']
        await send(msg)

    try:
        result = await call_next(scope, receive, _capture_send)
        elapsed = (time.monotonic() - start_ts) * 1000
        # Decode User-Agent (first 60 chars, never client IP)
        ua = ''
        for k, v in scope.get('headers', []):
            if k.decode('latin-1').lower() == 'user-agent':
                ua = v.decode('utf-8', errors='replace')
                break
        stats.record(
            method=scope.get('method', '?'),
            path=scope.get('path', '/'),
            status=response_status[0],
            http_version=scope.get('http_version', '1.1'),
            elapsed_ms=elapsed,
            user_agent=ua,
        )
        return result
    finally:
        stats.dec_connections()


# ===================================================================
# Helpers
# ===================================================================

def _http_version_label(http_version: str) -> str:
    """Convert ASGI ``http_version`` to a human-readable label."""
    if http_version == '2':
        return 'HTTP/2 (h2)'
    return f'HTTP/{http_version}' if http_version else 'HTTP/1.1'


def _get_route_list(app: BlackBull) -> list[dict[str, str]]:
    """Extract registered route templates from the internal router.

    Uses ``app._router._route_info`` (internal API).  Wrapped in a
    try/except to be safe against future API changes.
    """
    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    try:
        for ri in app._router._route_info:  # type: ignore[union-attr]
            template: str = ri.template
            methods = ri.methods
            if isinstance(methods, (list, tuple, set, frozenset)):
                method_list = [str(m) for m in methods]
            else:
                method_list = [str(methods)]
            for m in method_list:
                key = (m, template)
                if key not in seen:
                    seen.add(key)
                    routes.append({'method': m, 'path': template, 'note': ''})
    except Exception:
        pass  # Internal API may change; degrade gracefully

    # Annotate HTCPCP routes for dashboard clarity
    _htcpcp_notes = {
        ('POST', '/pot'): 'HTCPCP BREW',
        ('GET', '/pot'): 'HTCPCP pot state',
        ('GET', '/pot/when'): 'HTCPCP when',
    }
    for r in routes:
        note = _htcpcp_notes.get((r['method'], r['path']))
        if note:
            r['note'] = note

    # Sort: static paths first, then parameterised
    def _sort_key(r: dict[str, str]) -> tuple[int, str, str]:
        return (1 if '{' in r['path'] else 0, r['path'], r['method'])
    routes.sort(key=_sort_key)
    return routes


# ===================================================================
# Entry point
# ===================================================================

if __name__ == '__main__':
    _app = create_app()
    _port = int(os.environ.get('BB_PORT', '8000'))
    _max_conn = int(os.environ.get('BB_MAX_CONNECTIONS', '20'))
    _workers = int(os.environ.get('BB_WORKERS', '1'))
    _app.run(port=_port, max_connections=_max_conn, workers=_workers)
