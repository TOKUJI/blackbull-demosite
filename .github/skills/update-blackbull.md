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

### 5. Create PRs (Squash & Merge)
- PR `feature/bump-blackbull-<NEW_VERSION>` → `develop`
- PR `develop` → `main`

### 6. Verify deployment
- Watch GitHub Actions: `.github/workflows/deploy.yml`
- Check live health: `curl https://blackbull.alwaysdata.net/health`
- Expected: `"status":"ok"`, `"version"` reflects new BlackBull
