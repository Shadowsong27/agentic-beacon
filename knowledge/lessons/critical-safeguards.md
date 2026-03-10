# Lesson: Critical Project Safeguards

**Last Updated:** 2026-03-07
**Context:** Agentic Beacon Framework

---

## Overview

Essential guardrails to prevent common mistakes in the Agentic Beacon project.

## Safeguards

### 1. Never Commit Secrets

**Rule:** PyPI tokens, API keys, and credentials must NEVER be committed to the repository.

**Where secrets belong:**
- GitHub Secrets (for CI/CD workflows)
- Local environment variables
- Secure credential stores

**How to check:**
```bash
# Before committing, verify no secrets
git diff | grep -i "pypi-"
git diff | grep -i "token"
git diff | grep -i "api_key"
```

**If secret is committed:**
1. Immediately revoke the token/key
2. Remove from git history (`git filter-branch` or BFG Repo-Cleaner)
3. Generate new token/key
4. Update GitHub Secrets

### 2. Keep Examples Updated

**Rule:** `examples/sample-warehouse/` must always match `abc init` output exactly.

**When to update:**
- After any change to `libs/beacon/src/beacon/initializer.py`
- After modifying warehouse structure
- After updating placeholder templates

**How to update:**
```bash
rm -rf examples/sample-warehouse
cd examples
abc init sample-warehouse --org "Example Corp" --languages python,typescript --domains data-platform,web-services
```

### 3. Test Before Release

**Rule:** Always test CLI commands locally before pushing commits that will trigger release.

**Test commands:**
```bash
abc --version
abc init test-warehouse
abc setup --warehouse test-warehouse --all
abc list --warehouse test-warehouse
abc status
```

**Why this matters:**
- Release-Please auto-creates releases from conventional commits
- Bugs in releases create support burden
- PyPI doesn't allow re-uploading same version

### 4. Document Breaking Changes

**Rule:** Use `feat!:` or `fix!:` for breaking changes to trigger major version bump.

**Breaking change examples:**
- Removing CLI commands or options
- Changing warehouse structure in incompatible ways
- Modifying file formats that require migration

**Commit format:**
```bash
git commit -m "feat!: change warehouse context naming convention

BREAKING CHANGE: Context files now use .md extension instead of no extension"
```

## Verification Checklist

Before each commit:
- [ ] No secrets in diff
- [ ] Examples match current `abc init` output
- [ ] All CLI commands tested locally
- [ ] Breaking changes marked with `!`
- [ ] Tests passing
- [ ] Documentation updated
