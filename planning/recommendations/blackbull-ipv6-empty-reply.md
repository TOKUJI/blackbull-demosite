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

## Hypothesis

The issue is likely in BlackBull's **connection actor / protocol
detection layer**.  The TCP connection is accepted on the IPv6 socket,
but the HTTP/1.1 request-line parser (`readuntil(b'\r\n')`) may be
reading from the wrong transport or encountering a framing issue
specific to the IPv6 data path.

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
