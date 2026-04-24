# Fact: Release Workflow

**Last Updated:** 2026-04-24
**Context:** Agentic Beacon Framework

---

## Overview

Automated release workflow using Release-Please and GitHub Actions.

## Process

1. **Push conventional commits** to main branch
2. **Release-Please creates PR** with version bump and changelog
3. **Merge the Release-Please PR** — creates the GitHub release and version tag
4. **Create the release branch** from the tag — this triggers PyPI publish:
   ```bash
   git fetch origin
   git push origin refs/tags/agentic-beacon@vX.X.X:refs/heads/release/vX.X.X
   ```
5. **Package published** to PyPI automatically (plus platform bundles on the GitHub release)
6. **Verify on PyPI:**
   ```bash
   curl -s https://pypi.org/pypi/agentic-beacon/json | python3 -c \
     "import sys,json; d=json.load(sys.stdin); print(d['info']['version'])"
   ```

## Conventional Commits

- `feat:` → **minor** version bump (1.0.0 → 1.1.0)
- `fix:` → **patch** version bump (1.0.0 → 1.0.1)
- `feat!:` or `fix!:` → **major** version bump (1.0.0 → 2.0.0)
- `docs:`, `chore:`, `ci:`, `test:` → No version bump

## Release Branches

**Important:** Release branches are **permanent snapshots** - NEVER delete them.

**Purpose:**
- Historical reference (exact state at each release)
- Hotfix base (branch from `release/vX.X.X` for fixes)
- Audit trail (permanent record of PyPI publishes)
- Rollback reference (compare or revert to specific releases)

**Example:**
```
main (active development)
release/v1.0.0 (permanent)
release/v1.1.0 (permanent)
release/v1.2.0 (permanent)
```

## GitHub Actions

**Workflows:**
- `.github/workflows/release-please.yml` - Creates release PRs
- `.github/workflows/publish-pypi.yml` - Publishes to PyPI
- `.github/workflows/test-build.yml` - CI testing

**Required Secrets:**
- `PYPI_API_TOKEN` - PyPI API token for publishing

**Repository Settings:**
- Workflow permissions: "Read and write permissions"
- Allow GitHub Actions to create/approve PRs: Enabled

## Manual Release

If needed, trigger manually:
```bash
gh workflow run release-please.yml
```

## Monitoring

```bash
# View releases
gh release list

# View workflow runs
gh run list --workflow=publish-pypi.yml
```
