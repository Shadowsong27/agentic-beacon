# GitHub Actions CI/CD Setup

## Overview

Two workflows are configured for Agentic Beacon:

1. **test-build.yml** - Runs on every push/PR to validate builds
2. **publish-pypi.yml** - Publishes to PyPI on releases or manual trigger

## Setup Required

### 1. PyPI API Tokens

You need to create API tokens on PyPI for automated publishing.

#### For Production PyPI

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with scope: "Entire account" or "Project: agentic-beacon"
3. Copy the token (starts with `pypi-...`)
4. Add to GitHub Secrets:
   - Go to: https://github.com/Shadowsong27/agentic-beacon/settings/secrets/actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: `pypi-...` (your token)

#### For Test PyPI (Optional)

1. Go to https://test.pypi.org/manage/account/token/
2. Create a new API token
3. Add to GitHub Secrets:
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: `pypi-...` (your token)

### 2. Verify Secrets

Check secrets are set:
```bash
gh secret list --repo Shadowsong27/agentic-beacon
```

Should show:
- `PYPI_API_TOKEN`
- `TEST_PYPI_API_TOKEN` (if using TestPyPI)

## Workflows

### Test Build Workflow

**Triggers:**
- Push to main branch (changes in `libs/beacon/`)
- Pull requests (changes in `libs/beacon/`)

**What it does:**
1. Builds the package
2. Verifies package structure
3. Tests CLI installation
4. Reports status

**Manual trigger:**
```bash
gh workflow run test-build.yml
```

### PyPI Publish Workflow

**Triggers:**
- GitHub Release created (auto-publishes to production PyPI)
- Manual dispatch (choose production or test)

**What it does:**
1. Builds the package
2. Publishes to PyPI or TestPyPI
3. Creates release comment with install instructions
4. Reports status

**Manual trigger (TestPyPI):**
```bash
gh workflow run publish-pypi.yml -f environment=test
```

**Manual trigger (Production PyPI):**
```bash
gh workflow run publish-pypi.yml -f environment=production
```

## Publishing Workflow

### Option 1: Automated Release (Recommended)

1. Update version in `libs/beacon/pyproject.toml` and `__init__.py`
2. Commit and push:
   ```bash
   git add libs/beacon/pyproject.toml libs/beacon/src/beacon/__init__.py
   git commit -m "chore: bump version to 1.0.1"
   git push origin main
   ```
3. Create a GitHub release:
   ```bash
   gh release create v1.0.1 \
     --title "Agentic Beacon 1.0.1" \
     --notes "Release notes here"
   ```
4. Workflow automatically publishes to PyPI
5. Check status: https://github.com/Shadowsong27/agentic-beacon/actions

### Option 2: Manual Dispatch

**Test on TestPyPI first:**
```bash
gh workflow run publish-pypi.yml -f environment=test
```

Verify: `pip install --index-url https://test.pypi.org/simple/ agentic-beacon`

**Publish to production:**
```bash
gh workflow run publish-pypi.yml -f environment=production
```

Verify: `pip install agentic-beacon`

## Monitoring

### Check Workflow Status

```bash
# List recent workflow runs
gh run list --workflow=publish-pypi.yml

# View specific run
gh run view <run-id>

# View logs
gh run view <run-id> --log
```

### Check Package on PyPI

- **Production:** https://pypi.org/project/agentic-beacon/
- **Test:** https://test.pypi.org/project/agentic-beacon/

## Troubleshooting

### "Invalid credentials" error

- Verify secret is set: `gh secret list`
- Check token has correct permissions on PyPI
- Token format should be: `pypi-...` (not username/password)

### "Package already exists" error

- Version already published to PyPI
- Bump version in `pyproject.toml`
- PyPI doesn't allow re-uploading same version

### Build fails

- Check test-build workflow first
- Verify `pyproject.toml` is correct
- Check Python version requirements

### CLI not found after install

- Check `[project.scripts]` in `pyproject.toml`
- Should have: `abc = "beacon.cli:main"`
- Rebuild: `uv build`

## Testing Locally

Before publishing, test the build locally:

```bash
cd libs/beacon

# Build
uv build

# Install locally
pip install dist/*.whl

# Test
abc --version
abc --help
abc init test-warehouse
```

## Security Notes

- **Never commit API tokens** to the repository
- Tokens are stored securely in GitHub Secrets
- Tokens are only accessible to workflow runs
- Use scoped tokens (project-specific) when possible
- Rotate tokens regularly

## Next Steps After Setup

1. ✅ Set up `PYPI_API_TOKEN` secret
2. ✅ Test with manual workflow dispatch to TestPyPI
3. ✅ Verify installation from TestPyPI
4. ✅ Create first release to publish to production PyPI
5. ✅ Monitor workflow runs
6. ✅ Update README with installation badge

## Installation Badge

After first publish, add to README.md:

```markdown
[![PyPI](https://img.shields.io/pypi/v/agentic-beacon.svg)](https://pypi.org/project/agentic-beacon/)
[![Python](https://img.shields.io/pypi/pyversions/agentic-beacon.svg)](https://pypi.org/project/agentic-beacon/)
```
