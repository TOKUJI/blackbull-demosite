# Skill: Update BlackBull version for the demo site

## When to use
When the user asks to update BlackBull to a newer version on the demo site,
or after upgrading `pyproject.toml` locally and needing to deploy.

## Architecture (reminder)
- **Local repo** (`~/work/blackbull-demosite`) — for development
- **Alwaysdata** — production. Git clones `main` branch at `~/blackbull-demo/`
- **GitHub Actions** — `.github/workflows/deploy.yml` triggers on push to `main`
- **Deploy steps in CI**: test → SSH git pull → pip install → API restart → health check

## Procedure: Update BlackBull version

### 1. Check latest version
```bash
pip index versions blackbull
```

### 2. Update pyproject.toml
```toml
dependencies = [
    "blackbull>=<NEW_VERSION>",
    "blackbull-htcpcp",
]
```

### 3. Install and test locally
```bash
source .venv/bin/activate
pip install --upgrade 'blackbull>=<NEW_VERSION>'
pytest tests/ -v
```

### 4. Commit and push to feature branch
```bash
git checkout -b feature/bump-blackbull-<NEW_VERSION>
git add pyproject.toml
git commit -m "chore: bump blackbull to <NEW_VERSION>"
git push origin feature/bump-blackbull-<NEW_VERSION>
```

### 5. Create PRs
**Copilot** creates the PRs (via `gh pr create` or browser):
```bash
gh pr create --base develop --head feature/bump-blackbull-<NEW_VERSION> \
  --title "chore: bump blackbull to <NEW_VERSION>" \
  --body "## Changes ..."
```

**User** reviews and merges (Squash & Merge):
- PR `feature/bump-blackbull-<NEW_VERSION>` → `develop`
- PR `develop` → `main` (triggers `.github/workflows/deploy.yml`)

### 6. Verify deployment (User)
- Watch GitHub Actions: `.github/workflows/deploy.yml`
- Check live health: `curl https://blackbull.alwaysdata.net/health`
- Expected: `"status":"ok"`, `"version"` reflects new BlackBull

## Role division
| Step | Who |
|---|---|
| Check version, edit `pyproject.toml` | Copilot |
| Local test (`pip install`, `pytest`) | Copilot |
| Commit & push to feature branch | Copilot |
| Create PR (`gh pr create`) | Copilot |
| Review & merge PRs (Squash & Merge) | **User** |
| Verify deployment on Alwaysdata | **User** |

> **Why user merges:** Merging to `main` triggers a live deployment to Alwaysdata.
> The user should control when this happens (e.g., after review, during maintenance
> windows, etc.).

## Troubleshooting: Version not updating after deploy

### Symptom
Site shows old BlackBull version after successful PR merge to `main`.

### Root cause (most likely)
The Alwaysdata Service **was not restarted**. The deploy job's `curl` call to the
Alwaysdata API used `curl -sS` (no `-f`/`--fail` flag), so HTTP 401/403/500
errors from the API were silently ignored. `set -e` did not catch them.

### Fix applied (2026-07-15)
- Changed `curl -sS` → `curl -fsS` (adds `--fail`)
- Captures and echoes API response for debugging
- Added `--upgrade` to `.venv/bin/pip install -e .`
- Added `python -c 'import blackbull; print(...)'` version verification step

### Manual recovery
If the automatic deploy didn't restart the service:
```bash
ssh <user>@ssh-<user>.alwaysdata.net
cd ~/blackbull-demo
git pull origin main
.venv/bin/pip install --upgrade -e .
# Then restart via Alwaysdata admin panel: Advanced > Services > restart
```
