"""Inline HTML templates for the BlackBull demo site.

CSS is served from ``/static/style.css`` via BlackBull's built-in
static file middleware.  No JavaScript frameworks, no CDN resources
(except Swagger UI loaded by BlackBull's built-in ``enable_openapi()``).

Design aesthetic: HAProxy-inspired transparency + Caddy-inspired
terminal look — dark background, monospace stats, clean layout.
Response size target: < 10 KB (HTML only; CSS is cached separately).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def _attr_escape(s: str) -> str:
    """Escape a string for safe inclusion in a double-quoted HTML attribute.

    Only escapes ``&`` and ``"`` — does **not** escape ``<`` or ``>``
    so that JavaScript arrow functions (``=>``) and comparisons survive.
    """
    return s.replace('&', '&amp;').replace('"', '&quot;')


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


def _format_bytes(n: int) -> str:
    """Format byte count for display."""
    if n < 1024:
        return str(n)
    elif n < 1024 * 1024:
        return f'{n / 1024:.1f}K'
    else:
        return f'{n / (1024 * 1024):.1f}M'


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
    _query_bodies: dict[str, str] = {
        '/api/changelog': '{"version":"0.59.0"}',
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
        elif path == '/api/methods' and method in ('POST', 'PUT'):
            js = f"methodDemo({method!r})"
            path_html = (
                f'<span class="route-link" onclick="{_attr_escape(js)}">'
                f'{path}</span>'
            )
        elif path == '/api/methods' and method == 'DELETE':
            # DELETE is self-explanatory — plain text.
            path_html = path
        elif method == 'QUERY':
            body = _query_bodies.get(path, '{}')
            js = (
                f"fetch({path!r},{{method:'QUERY'"
                f",headers:{{'Content-Type':'application/json'}}"
                f",body:{json.dumps(body)}"
                + "}).then(r=>r.text()).then(t=>{document.getElementById('bb-resp').textContent=t;refreshStats()})"
                + ".catch(e=>{document.getElementById('bb-resp').textContent='Error: '+e})"
            )
            path_html = f'<span class="route-link" onclick="{_attr_escape(js)}">{path}</span>'
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
            path_html = f'<span class="route-link" onclick="{_attr_escape(js)}">{path}</span>'
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
            f'<td class="bytes">{_format_bytes(req.get("bytes", 0))}</td>'
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

<h2>Connection</h2>
<div class="conn-info">
  <dl>
    <dt>Protocol</dt><dd class="{proto_badge_cls}">{proto_label}</dd>
  </dl>
</div>

<h2>Routes ({len(routes)})</h2>
<table>
  <thead><tr><th>Method</th><th>Path</th></tr></thead>
  <tbody>
    {''.join(route_rows)}
  </tbody>
</table>

<h2>Response</h2>
<pre id="bb-resp" class="resp-area">Click a route above.</pre>

<h2>Requests</h2>
<table>
  <thead><tr><th>Time (UTC)</th><th>Method</th><th>Path</th><th>Status</th><th>Proto</th><th>Bytes</th><th>Latency</th></tr></thead>
  <tbody id="bb-recent">
    {''.join(req_rows) if req_rows else '<tr><td colspan="7" style="color:var(--muted)">No requests yet.</td></tr>'}</
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
  Powered by BlackBull
</footer>

<script>
function fmtBytes(n){{
  if(n<1024)return n.toString();
  if(n<1048576)return (n/1024).toFixed(1)+'K';
  return (n/1048576).toFixed(1)+'M';
}}
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
        return '<tr><td class=time>'+r.time+'</td><td class=method>'+r.method+'</td><td class=path>'+r.path+'</td><td class='+cls+'>'+r.status+'</td><td class=proto>'+r.http_version+'</td><td class=bytes>'+fmtBytes(r.bytes||0)+'</td><td class=elapsed>'+lat+'</td></tr>';
      }}).join('');
    }}else{{
      tb.innerHTML = '<tr><td colspan=7 style=color:var(--muted)>No requests yet.</td></tr>';
    }}
  }});
}}
let _m='';
function methodDemo(m){{_m=m;var r=document.getElementById('bb-resp');r.innerHTML='<textarea id=bb-in style=width:100%;height:3em;background:var(--bg);color:var(--text);border:1px solid var(--line);padding:.3em;font:inherit placeholder=\"'+m+' /api/methods \u2014 type body, Enter...\"></textarea>';var t=document.getElementById('bb-in');t.focus();t.addEventListener('keydown',function(e){{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();sendDemo();}}}});}}
function sendDemo(){{var b=document.getElementById('bb-in').value;fetch('/api/methods',{{method:_m,headers:{{'Content-Type':'text/plain'}},body:b}}).then(function(r){{return r.text()}}).then(function(t){{document.getElementById('bb-resp').textContent=t;refreshStats()}}).catch(function(e){{document.getElementById('bb-resp').textContent='Error: '+e}});}}
</script>

</body>
</html>'''  # noqa: E501 (line length for inline HTML is intentional)
