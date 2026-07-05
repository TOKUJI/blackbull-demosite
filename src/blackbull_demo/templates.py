"""Inline HTML templates for the BlackBull demo site.

CSS is served from ``/static/style.css`` via BlackBull's built-in
static file middleware.  No JavaScript frameworks, no CDN resources
(except Swagger UI loaded by BlackBull's built-in ``enable_openapi()``).

Design aesthetic: HAProxy-inspired transparency + Caddy-inspired
terminal look — dark background, monospace stats, clean layout.
Response size target: < 10 KB (HTML only; CSS is cached separately).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _format_uptime(seconds: float) -> str:
    """Format uptime seconds into a human-readable string."""
    if seconds < 0:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts: List[str] = []
    if d:
        parts.append(f'{d}d')
    if h:
        parts.append(f'{h}h')
    if m:
        parts.append(f'{m}m')
    if not parts:
        parts.append(f'{s}s')
    return ' '.join(parts)


def _format_elapsed(ms: float) -> str:
    """Format elapsed milliseconds for display."""
    if ms < 1:
        return f'{ms * 1000:.0f}µs'
    elif ms < 1000:
        return f'{ms:.1f}ms'
    else:
        return f'{ms / 1000:.2f}s'


def render_dashboard(
    *,
    version: str,
    hostname: str,
    http_version: str,
    routes: List[Dict[str, Any]],
    stats: Dict[str, Any],
) -> str:
    """Render the HTML dashboard (GET /).

    Parameters
    ----------
    version:
        BlackBull version string (``blackbull.__version__``).
    hostname:
        Server hostname (``socket.gethostname()``).
    http_version:
        Client's HTTP version from ``scope['http_version']``.
    routes:
        List of dicts with ``method``, ``path``, and optional ``note`` keys.
    stats:
        Statistics dict from ``Stats.to_dict()``.
    """
    uptime_str = _format_uptime(stats['uptime_seconds'])
    avg_ms = stats['avg_response_time_ms']

    # Protocol badge
    is_h2 = http_version.startswith('HTTP/2')
    proto_badge_cls = 'proto-h2' if is_h2 else 'proto-h1'
    proto_label = http_version

    # Route rows
    route_rows: List[str] = []
    _param_demo: dict[str, str] = {'{name}': 'World', '{n:int}': '42'}
    _htcpcp_headers: dict[str, str] = {
        'BREW': "'Accept-Additions': 'Cream'",
        'POST': "'Accept-Additions': 'Cream'",
    }
    for r in routes:
        method = r.get('method', 'GET')
        path = r.get('path', '/')
        note = r.get('note', '')
        note_html = f' <span class="route-note">({note})</span>' if note else ''
        if method == 'GET':
            href = path
            for param, val in _param_demo.items():
                href = href.replace(param, val)
            path_html = f'<a href="{href}">{path}</a>'
        else:
            # HTCPCP headers only for /pot routes
            extra_hdr = ''
            if path.startswith('/pot'):
                extra_hdr = _htcpcp_headers.get(method, '')
            hdr_obj = f'{{{extra_hdr}}}' if extra_hdr else '{}'
            js = (
                f"fetch({path!r},{{method:{method!r}"
                + (f",headers:{hdr_obj}" if extra_hdr else "")
                + "}).then(r=>r.text()).then(t=>{document.getElementById('bb-resp').textContent=t;refreshStats()})"
                + ".catch(e=>{document.getElementById('bb-resp').textContent='Error: '+e})"
            )
            path_html = f'<span class="route-link" onclick="{js}">{path}</span>'
        route_rows.append(
            f'<tr><td class="method">{method}</td>'
            f'<td class="path">{path_html}{note_html}</td></tr>'
        )

    # Recent request rows
    req_rows: List[str] = []
    for req in stats.get('recent_requests', [])[:20]:
        status_cls = 'status-ok' if 200 <= req['status'] < 400 else 'status-err'
        elapsed = _format_elapsed(req['elapsed_ms'])
        req_rows.append(
            f'<tr>'
            f'<td class="time">{req["time"]}</td>'
            f'<td class="method">{req["method"]}</td>'
            f'<td class="path">{req["path"]}</td>'
            f'<td class="{status_cls}">{req["status"]}</td>'
            f'<td class="proto">{req["http_version"]}</td>'
            f'<td class="elapsed">{elapsed}</td>'
            f'</tr>'
        )

    return f'''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BlackBull Demo</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/style.css">
</head>
<body>

<h1><span class="emoji">🐂</span>BlackBull Demo</h1>
<p class="subtitle">Running BlackBull {version} on {hostname}</p>

<div class="cards">
  <div class="card">
    <div class="card-label">Status</div>
    <div class="card-value"><span class="status-dot online"></span>ONLINE</div>
  </div>
  <div class="card">
    <div class="card-label">Protocol</div>
    <div class="card-value {proto_badge_cls}">{proto_label}</div>
  </div>
  <div class="card">
    <div class="card-label">Uptime</div>
    <div class="card-value">{uptime_str}</div>
  </div>
</div>

<h2>Your Connection</h2>
<div class="conn-info">
  <dl>
    <dt>Protocol</dt><dd class="{proto_badge_cls}">{proto_label}</dd>
    <dt>Encryption</dt><dd>{"TLS (direct — BlackBull ALPN)" if is_h2 else "TLS (Alwaysdata edge — Let's Encrypt)"}</dd>
  </dl>
</div>

<h2>Registered Routes ({len(routes)})</h2>
<table>
  <thead><tr><th>Method</th><th>Path</th></tr></thead>
  <tbody>
    {''.join(route_rows)}
  </tbody>
</table>

<h2>Response</h2>
<pre id="bb-resp" class="resp-area">Click a non-GET route above to see the response here.</pre>

<h2>Recent Requests</h2>
<table>
  <thead><tr><th>Time (UTC)</th><th>Method</th><th>Path</th><th>Status</th><th>Proto</th><th>Latency</th></tr></thead>
  <tbody id="bb-recent">
    {''.join(req_rows) if req_rows else '<tr><td colspan="6" style="color:var(--muted)">No requests yet.</td></tr>'}
  </tbody>
</table>

<h2>Statistics</h2>
<div class="stats-summary">
  <div class="stat-item">
    <div class="stat-value" id="bb-total">{stats['total_requests']:,}</div>
    <div class="stat-label">Total Requests</div>
  </div>
  <div class="stat-item">
    <div class="stat-value" id="bb-avg">{avg_ms:.1f} ms</div>
    <div class="stat-label">Avg Response Time</div>
  </div>
</div>

<footer>
  <a href="https://github.com/TOKUJI/BlackBull">GitHub</a> ·
  <a href="https://pypi.org/project/blackbull/">PyPI</a> ·
  <a href="/docs">Swagger UI</a> ·
  <a href="/openapi.json">OpenAPI</a> ·
  <a href="/health">Health</a><br>
  Powered by BlackBull — no uvicorn, no gunicorn, no hypercorn.
</footer>

<script>
function refreshStats(){{
  fetch('/stats.json').then(r=>r.json()).then(d=>{{
    document.getElementById('bb-total').textContent = d.total_requests.toLocaleString();
    document.getElementById('bb-avg').textContent = d.avg_response_time_ms.toFixed(1)+' ms';
    const tb = document.getElementById('bb-recent');
    const rows = d.recent_requests.slice(0,20);
    if(rows.length){{
      tb.innerHTML = rows.map(r=>{{
        const cls = r.status>=200&&r.status<400?'status-ok':'status-err';
        let lat;
        if(r.elapsed_ms<1) lat=(r.elapsed_ms*1000).toFixed(0)+'µs';
        else if(r.elapsed_ms<1000) lat=r.elapsed_ms.toFixed(1)+'ms';
        else lat=(r.elapsed_ms/1000).toFixed(2)+'s';
        return '<tr><td class=time>'+r.time+'</td><td class=method>'+r.method+'</td><td class=path>'+r.path+'</td><td class='+cls+'>'+r.status+'</td><td class=proto>'+r.http_version+'</td><td class=elapsed>'+lat+'</td></tr>';
      }}).join('');
    }}else{{
      tb.innerHTML = '<tr><td colspan=6 style=color:var(--muted)>No requests yet.</td></tr>';
    }}
  }});
}}
</script>

</body>
</html>'''  # noqa: E501 (line length for inline HTML is intentional)
