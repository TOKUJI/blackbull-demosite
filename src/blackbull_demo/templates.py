"""Inline HTML templates for the BlackBull demo site.

ALL CSS is inlined in ``<style>`` tags.  No external stylesheets, no
JavaScript frameworks, no CDN resources (except Swagger UI loaded by
BlackBull's built-in ``enable_openapi()``).

Design aesthetic: HAProxy-inspired transparency + Caddy-inspired
terminal look — dark background, monospace stats, clean layout.
Response size target: < 10 KB.
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

    # Route rows
    route_rows: List[str] = []
    for r in routes:
        method = r.get('method', 'GET')
        path = r.get('path', '/')
        note = r.get('note', '')
        note_html = f' <span class="route-note">({note})</span>' if note else ''
        route_rows.append(
            f'<tr><td class="method">{method}</td>'
            f'<td class="path">{path}{note_html}</td></tr>'
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
<style>
:root {{
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #c9d1d9;
  --muted: #8b949e;
  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --orange: #d2991d;
  --font: 'SF Mono', 'Cascadia Code', 'JetBrains Mono', 'Fira Code', monospace;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{
  background:var(--bg);color:var(--text);font-family:var(--font);
  font-size:13px;line-height:1.5;padding:20px;max-width:960px;margin:0 auto;
}}
h1{{font-size:20px;font-weight:600;margin-bottom:4px}}
h1 .emoji{{margin-right:6px}}
h2{{font-size:15px;font-weight:600;margin:20px 0 8px;color:var(--accent)}}
.subtitle{{color:var(--muted);font-size:12px;margin-bottom:16px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
.card{{
  background:var(--surface);border:1px solid var(--border);
  border-radius:6px;padding:12px 16px;flex:1;min-width:140px
}}
.card-label{{color:var(--muted);font-size:10px;text-transform:uppercase}}
.card-value{{font-size:18px;font-weight:600;margin-top:2px}}
.status-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
.status-dot.online{{background:var(--green)}}
table{{width:100%;border-collapse:collapse;margin-bottom:12px}}
th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid var(--border);white-space:nowrap}}
th{{color:var(--muted);font-size:10px;text-transform:uppercase;font-weight:500}}
td.method{{color:var(--accent);font-weight:600;min-width:48px}}
td.path{{font-family:var(--font)}}
td.time{{color:var(--muted)}}
td.status-ok{{color:var(--green)}}
td.status-err{{color:var(--red)}}
td.proto,td.elapsed{{color:var(--muted)}}
.route-note{{color:var(--orange);font-weight:400}}
.conn-info{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:12px 16px;margin-bottom:16px}}
.conn-info dl{{display:grid;grid-template-columns:120px 1fr;gap:4px 12px}}
.conn-info dt{{color:var(--muted);font-size:11px}}
.conn-info dd{{font-size:13px}}
.stats-summary{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px}}
.stat-item{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:10px 14px;flex:1;min-width:120px}}
.stat-value{{font-size:17px;font-weight:600}}
.stat-label{{color:var(--muted);font-size:10px;text-transform:uppercase}}
footer{{margin-top:24px;padding-top:12px;border-top:1px solid var(--border);color:var(--muted);font-size:11px}}
footer a{{color:var(--accent);text-decoration:none}}
footer a:hover{{text-decoration:underline}}
@media (prefers-color-scheme:light){{
  :root{{--bg:#fff;--surface:#f6f8fa;--border:#d0d7de;--text:#1f2328;--muted:#656d76}}
}}
</style>
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
    <div class="card-value">{http_version}</div>
  </div>
  <div class="card">
    <div class="card-label">Uptime</div>
    <div class="card-value">{uptime_str}</div>
  </div>
</div>

<h2>Your Connection</h2>
<div class="conn-info">
  <dl>
    <dt>Protocol</dt><dd>{http_version}</dd>
    <dt>Encryption</dt><dd>TLS (Alwaysdata edge)</dd>
  </dl>
</div>

<h2>Registered Routes ({len(routes)})</h2>
<table>
  <thead><tr><th>Method</th><th>Path</th></tr></thead>
  <tbody>
    {''.join(route_rows)}
  </tbody>
</table>

<h2>Recent Requests</h2>
<table>
  <thead><tr><th>Time</th><th>Method</th><th>Path</th><th>Status</th><th>Proto</th><th>Latency</th></tr></thead>
  <tbody>
    {''.join(req_rows) if req_rows else '<tr><td colspan="6" style="color:var(--muted)">No requests yet.</td></tr>'}
  </tbody>
</table>

<h2>Statistics</h2>
<div class="stats-summary">
  <div class="stat-item">
    <div class="stat-value">{stats['total_requests']:,}</div>
    <div class="stat-label">Total Requests</div>
  </div>
  <div class="stat-item">
    <div class="stat-value">{stats['active_connections']}</div>
    <div class="stat-label">Active Connections</div>
  </div>
  <div class="stat-item">
    <div class="stat-value">{avg_ms:.1f} ms</div>
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

</body>
</html>'''  # noqa: E501 (line length for inline HTML is intentional)
