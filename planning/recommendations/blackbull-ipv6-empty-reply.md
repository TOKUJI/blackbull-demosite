# BlackBull IPv6 — TCP handshake succeeds but HTTP response is empty

## Symptoms

BlackBull binds to IPv6 (`::` or a specific IPv6 address) and accepts TCP
connections, but every HTTP request receives an **empty reply** — the
connection is closed without any HTTP response bytes.

IPv4 on the same host works correctly.

```bash
# IPv4 — works
$ curl -s http://127.0.0.1:8000/health
{"status":"ok"}

# IPv6 — empty reply (TCP handshake OK, no HTTP bytes)
$ curl -sv http://[::1]:8000/health 2>&1
* Connected to ::1 (::1) port 8000
> GET /health HTTP/1.1
...
* Empty reply from server
```

## Steps to Reproduce

Minimal reproduction (any BlackBull version, any Python 3.11–3.13):

```python
from blackbull import BlackBull

app = BlackBull()

@app.route(path='/')
async def hello():
    return 'OK'

app.run(port=8100)
```

```bash
# IPv4 — OK
curl http://127.0.0.1:8100/
# → "OK"

# IPv6 — empty reply
curl http://[::1]:8100/
# → Empty reply from server
```

## Environment

| | Local (RyzenPC) | Alwaysdata |
|---|---|---|
| Python | 3.12.3 | 3.13.x |
| BlackBull | 0.48.0 | 0.48.0 |
| OS | Ubuntu 24.04 | Debian (Alwaysdata) |
| IPv4 | ✅ Works | ✅ Works |
| IPv6 | ❌ Empty reply | ❌ Empty reply |

## Observations

- `ss -tlnp` shows BlackBull listening on both IPv4 and IPv6 sockets.
- `curl -sv` confirms **TCP handshake succeeds** on both protocols.
- The `--bind` host value is marked "advisory in v1" by BlackBull; it
  always binds dual-stack.
- Debug logging (`BLACKBULL_ENV=development`) shows the ASGI scope is
  correctly built and the handler returns normally on IPv4.  On IPv6
  the debug output is absent — the request never reaches the ASGI
  application layer.

## Root Cause

**File:** `blackbull/server/http1_actor.py`, Host header parsing (~L685)

```python
# Current code (broken for IPv6):
if headers.getlist(b'host'):
    parts = headers.get(b'host').split(b':')
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else _DEFAULT_PORT
    scope['server'] = [host.decode('utf-8'), port]
```

`b'[::1]:8100'.split(b':')` produces `[b'[', b'', b'1]', b'8100']`.
`int(b'')` raises `ValueError`.

This `ValueError` is **not** caught by `HTTP1Actor.run()` (which only
handles `HeaderTooLargeError`, `BadRequestError`, and
`NotImplementedFramingError`).  It propagates to
`ConnectionActor.run()`'s generic `except Exception`, which silently
closes the transport with `await self._writer.close()`.  No HTTP
response bytes are ever written — hence "Empty reply from server."

cf. RFC 3986 §3.2.2 — IPv6 addresses in URIs use bracket notation:
`[::1]:port`.

## Proposed Fix

```python
if headers.getlist(b'host'):
    host_value = headers.get(b'host')
    if host_value.startswith(b'['):
        # IPv6 bracket notation: [::1]:8100
        close = host_value.find(b']')
        if close != -1:
            host = host_value[1:close]
            port_str = host_value[close + 1:]
            port = int(port_str[1:]) if port_str.startswith(b':') else _DEFAULT_PORT
        else:
            parts = host_value.split(b':')
            host, port = parts[0], int(parts[1]) if len(parts) > 1 else _DEFAULT_PORT
    else:
        # IPv4 / bare hostname
        parts = host_value.split(b':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else _DEFAULT_PORT
    scope['server'] = [host.decode('utf-8'), port]
```

### Secondary: IPv6 address tuple normalization

`server/server.py` `_serve_connection` (~L322) normalizes AF_UNIX
addresses to 2-tuples but leaves AF_INET6 4-tuples
`(host, port, flowinfo, scope_id)` un-normalized, producing
non-ASGI-compliant `['::1', port, 0, 0]` in `scope['client']` and
`scope['server']`.  These should be truncated to 2-tuples per the ASGI
spec.

## Impact

This blocks deployment on **Alwaysdata**, whose reverse proxy connects
to user applications exclusively over IPv6.  The `User Program` site
type provides `$IP = ::` and `$PORT = 8100`; applications must accept
IPv6 connections.

## Workaround

Use an IPv4 reverse-proxy target.  On Alwaysdata this means switching
the site type from "User program" to "Reverse proxy" and pointing the
target at the **IPv4** address shown by `ss -tlnp` (e.g.
`http://127.7.109.100:8100`).  This bypasses the IPv6 data path
entirely.

## Related

- BlackBull `--bind` advisory note: `"host '...' is advisory in v1;
  binding dual-stack on port ... for now."`
- Alwaysdata reverse proxy always connects via IPv6 (`$IP = ::`).
