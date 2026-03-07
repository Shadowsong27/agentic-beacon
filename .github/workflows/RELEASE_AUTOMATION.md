# Release Automation Complete!

## ✅ What's Set Up

### 1. Release-Please Workflow
Automated version management using conventional commits.

**Triggers:**
- Push to main (automatic)
- Manual dispatch (custom versions)

**What it does:**
1. Analyzes conventional commits (feat:, fix:, etc.)
2. Determines version bump (major/minor/patch)
3. Creates PR with version bump and changelog
4. When PR merged → creates GitHub release
5. Triggers PyPI publish automatically

### 2. PyPI Publish Workflow
Automated package publishing.

**Triggers:**
- GitHub release created (automatic from release-please)
- Manual dispatch (test/production)
- Workflow call (from release-please)

### 3. Test Build Workflow
Continuous integration on every push.

**Triggers:**
- Push/PR to main

## 🔑 Setup PyPI API Token

### Quick Setup

```bash
# 1. Create token on PyPI
# Go to: https://pypi.org/manage/account/token/
# Scope: "Entire account" (for first upload)
# Copy the token (starts with pypi-)

# 2. Add to GitHub
gh secret set PYPI_API_TOKEN --repo Shadowsong27/agentic-beacon
# Paste your token when prompted

# 3. Verify
gh secret list --repo Shadowsong27/agentic-beacon
```

**Complete guide:** See `.github/workflows/PYPI_TOKEN_SETUP.md`

## 🚀 How to Release

### Automatic Release (Recommended)

**Using Conventional Commits:**

```bash
# Make changes
git add .

# Commit with conventional format
git commit -m "feat: add new warehouse sync feature"
# Or: fix:, docs:, refactor:, chore:, etc.

# Push to main
git push origin main
```

**What happens:**
1. Release-please detects conventional commit
2. Creates/updates PR with version bump
3. You review and merge the PR
4. Release-please creates GitHub release
5. PyPI publish workflow runs automatically
6. Package published to PyPI! 🎉

### Manual Release

**Force a release with custom version:**

```bash
# Trigger manual release
gh workflow run release-please.yml \
  -f release_type=minor \
  -f custom_version=1.1.0 \
  -f reason="Adding important feature"
```

**Options:**
- `release_type`: `patch` (1.0.1), `minor` (1.1.0), `major` (2.0.0)
- `custom_version`: Exact version (optional)
- `reason`: Why releasing (optional)

## 📊 Monitor Releases

```bash
# View workflow runs
gh run list --workflow=release-please.yml

# View releases
gh release list

# View specific release
gh release view v1.0.0
```

## 🔄 Release Workflow

```
1. Push conventional commit
   ↓
2. Release-please creates PR
   - Updates version in pyproject.toml
   - Updates version in __init__.py  
   - Generates CHANGELOG.md
   ↓
3. Review and merge PR
   ↓
4. Release-please creates GitHub release
   - Tag: agentic-beacon@v1.0.0
   - Release notes from changelog
   ↓
5. PyPI publish workflow triggers
   - Builds package
   - Publishes to PyPI
   ↓
6. Users can install
   pip install agentic-beacon
```

## 📝 Conventional Commit Types

| Type | Version Bump | Example |
|------|--------------|---------|
| `feat:` | minor (1.0.0 → 1.1.0) | `feat: add delta command` |
| `fix:` | patch (1.0.0 → 1.0.1) | `fix: resolve CLI crash` |
| `feat!:` | major (1.0.0 → 2.0.0) | `feat!: change API structure` |
| `fix!:` | major (1.0.0 → 2.0.0) | `fix!: remove deprecated flags` |
| `refactor:` | patch | `refactor: simplify init logic` |
| `perf:` | patch | `perf: optimize file copying` |
| `docs:` | none | `docs: update README` |
| `chore:` | none | `chore: update dependencies` |
| `ci:` | none | `ci: fix workflow` |
| `test:` | none | `test: add unit tests` |

**Breaking changes:** Add `!` after type (e.g., `feat!:`) or include `BREAKING CHANGE:` in footer

## 🧪 Testing Before Production

**Test on TestPyPI first:**

```bash
# 1. Set test PyPI token
gh secret set TEST_PYPI_API_TOKEN --repo Shadowsong27/agentic-beacon

# 2. Trigger test publish
gh workflow run publish-pypi.yml -f environment=test

# 3. Test install
pip install --index-url https://test.pypi.org/simple/ agentic-beacon

# 4. Verify
abc --version
abc init test-warehouse
```

## 📋 First Release Checklist

- [ ] Create PyPI account (https://pypi.org)
- [ ] Generate API token (scope: "Entire account")
- [ ] Add token to GitHub: `gh secret set PYPI_API_TOKEN`
- [ ] Verify secret: `gh secret list`
- [ ] Push a conventional commit: `feat: initial release`
- [ ] Review release-please PR
- [ ] Merge PR
- [ ] Verify release created on GitHub
- [ ] Verify package on PyPI: https://pypi.org/project/agentic-beacon/
- [ ] Test install: `pip install agentic-beacon`
- [ ] Test CLI: `abc --version`

## 🎯 Current Status

- **Version:** 1.0.0
- **Status:** Production/Stable
- **Release automation:** ✅ Ready
- **PyPI publish:** ⏳ Waiting for PYPI_API_TOKEN secret

## 🔧 Troubleshooting

### Release PR not created

- Check conventional commit format: `feat:`, `fix:`, etc.
- View workflow run: `gh run list --workflow=release-please.yml`
- Check logs: `gh run view <run-id> --log`

### PyPI publish failed

- Verify token: `gh secret list`
- Check token hasn't expired
- For first upload, use "Entire account" scope
- View workflow logs: `gh run list --workflow=publish-pypi.yml`

### Can't install from PyPI

- Check package exists: https://pypi.org/project/agentic-beacon/
- Wait a few minutes for PyPI propagation
- Try with version: `pip install agentic-beacon==1.0.0`

## 📚 Documentation

- **Release-Please:** `.github/workflows/release-please.yml`
- **PyPI Publish:** `.github/workflows/publish-pypi.yml`
- **Token Setup:** `.github/workflows/PYPI_TOKEN_SETUP.md`
- **Workflow Setup:** `.github/workflows/SETUP.md`
- **Release Guide:** `libs/beacon/PYPI_RELEASE.md`

## 🎉 Summary

**Everything is automated!**

1. ✅ Write code
2. ✅ Commit with `feat:` or `fix:`
3. ✅ Push to main
4. ✅ Merge release PR
5. ✅ Package auto-publishes to PyPI!

**Just add the PyPI token and you're ready to go!** 🚀
