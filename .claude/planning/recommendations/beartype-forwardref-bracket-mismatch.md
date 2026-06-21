# Beartype Code-Generation Bug in BlackBull 0.43.0 Route Validation

**Date:** 2026-06-21  
**Severity:** High — blocks all integration tests  
**Status:** Open  
**Reported against:** `blackbull==0.43.0` + `beartype==0.22.8`

---

## Summary

During lifespan startup, `blackbull` calls `self._router.validate()` which
invokes `beartype.die_if_unbearable()` on route parameter annotations. Beartype's
code generator emits invalid Python containing a mismatched bracket:
`${FORWARDREF:str]?}` — an opening `{` paired with a closing `]`.

This causes a `SyntaxError` at `compile()` time, which surfaces as a
`RuntimeError: Lifespan startup failed` in `blackbull.testing._LifespanManager`.

---

## Environment

| Component | Version |
|---|---|
| Python | 3.12.3 |
| blackbull | 0.43.0 |
| beartype | 0.22.8 (also reproduced with 0.22.9) |
| OS | Linux (WSL) |

---

## Steps to Reproduce

```python
from blackbull_demo.app import create_app
from blackbull.testing import TestClient

app = create_app()
with TestClient(app) as c:
    c.get("/health")
```

Or simply:

```bash
pytest tests/test_app.py -v
```

All 21 integration tests fail identically; 8 unit tests in `test_stats.py`
(no beartype involvement) pass.

---

## Traceback (abbreviated)

```
File "beartype/_util/func/utilfuncmake.py", line 271, in make_func
    func_code_compiled = compile(func_code, func_filename, 'exec')
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<@beartype(__beartype_checker_0) ...>", line 11
    if not isinstance(__beartype_pith_0, ${FORWARDREF:str]?):
                                                         ^
SyntaxError: closing parenthesis ']' does not match opening parenthesis '{'

The above exception was the direct cause of ...

File "blackbull/app.py", line 398, in _handle_lifespan
    self._router.validate()
File "blackbull/router.py", line 917, in validate
    die_if_unbearable(sample, p.annotation)
...
RuntimeError: Lifespan startup failed: _BeartypeUtilCallableException(...)
```

### Full call chain

```
blackbull.testing.TestClient.__enter__
  → blackbull.testing._LifespanManager.startup
    → blackbull.app.BlackBull.__call__              # lifespan ASGI message
      → blackbull.app.BlackBull._handle_lifespan
        → blackbull.router.Router.validate          # line 917
          → beartype.die_if_unbearable(sample, p.annotation)
            → beartype._check.checkmake._make_func_checker
              → beartype._util.func.utilfuncmake.make_func
                → compile()  💥 SyntaxError
```

---

## Analysis

### What happens

1. `Router.validate()` iterates over registered route parameters and calls
   `die_if_unbearable(sample, p.annotation)` for each one (router.py:917).
2. For a parameter annotated with a forward-reference `str` type hint,
   beartype's checker factory generates a Python function body containing the
   malformed token `${FORWARDREF:str]?}`.
3. The opening delimiter `$` looks like a string-substitution placeholder
   (beartype uses `${...}` for forward references internally), but the
   closing bracket is `]` instead of `}`.
4. `compile()` rejects it as a syntax error.

### Likely root cause

Beartype's forward-reference string-substitution mechanism is producing an
unbalanced bracket. The generated code:

```python
if not isinstance(__beartype_pith_0, ${FORWARDREF:str]?):
```

…should instead read something like:

```python
if not isinstance(__beartype_pith_0, str):
```

The `]?` suffix suggests a regex-like optional-closing-bracket pattern leaked
into the code template — possibly from a regex used internally by beartype to
parse string annotations.

### Why unit tests pass

`tests/test_stats.py` tests the `Stats` class in isolation. No BlackBull
application is created, no router validation occurs, and no beartype type
checking is invoked.

### Impact

- **All** integration tests (`tests/test_app.py`) are blocked.
- The production `app.run()` path may also be affected — untested because
  `TestClient` triggers the same lifespan codepath as the real server.
- 21 of 29 total tests error out (8 pass).

---

## Workarounds (for this project)

1. **Skip integration tests** and run only unit tests:
   ```bash
   pytest tests/test_stats.py -v
   ```

2. **Pin beartype to a known-good version** (tried 0.22.8, 0.22.9 — both fail).

3. **Monkey-patch `Router.validate`** to skip `die_if_unbearable` calls
   (not recommended for production).

4. **Wait for upstream fix** in either blackbull or beartype.

---

## Recommendations

| Priority | Action | Owner |
|---|---|---|
| P0 | File issue on blackbull repo with this repro | blackbull-demo team |
| P1 | Pin `beartype>=0.22.10` once fixed upstream | blackbull-demo team |
| P2 | Add `pytest.mark.skip` on integration tests referencing this issue | blackbull-demo team |
| P3 | Investigate whether `beartype < 0.22.8` resolves the issue | blackbull-demo team |

---

## References

- Beartype source: `beartype/_check/checkmake.py:777` — `_make_func_checker`
- Beartype source: `beartype/_util/func/utilfuncmake.py:271` — `make_func`
- BlackBull source: `blackbull/router.py:917` — `Router.validate`
- BlackBull source: `blackbull/app.py:398` — `_handle_lifespan`
- BlackBull source: `blackbull/testing.py:186` — `_wait_for_lifespan_event`
