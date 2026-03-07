# Setting Up PyPI API Token

## Step 1: Create PyPI Account

1. Go to https://pypi.org/account/register/
2. Create an account with your email
3. Verify your email address

## Step 2: Generate API Token

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Fill in the form:
   - **Token name**: `agentic-beacon-github-actions`
   - **Scope**: Select "Project: agentic-beacon" (after first manual upload) OR "Entire account" (for first upload)
   - Click "Add token"

4. **IMPORTANT**: Copy the token immediately - it starts with `pypi-`
   - You'll see something like: `pypi-AgEIcHlwaS5vcmc...`
   - This token will NEVER be shown again!

## Step 3: Add Token to GitHub Secrets

### Option 1: Using GitHub CLI (Recommended)

```bash
# Set the token as a GitHub secret
gh secret set PYPI_API_TOKEN --repo Shadowsong27/agentic-beacon

# Paste your token when prompted (it will be hidden)
# The token should start with: pypi-
```

### Option 2: Using GitHub Web UI

1. Go to https://github.com/Shadowsong27/agentic-beacon/settings/secrets/actions
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: Paste your `pypi-` token
5. Click "Add secret"

## Step 4: Verify Secret is Set

```bash
gh secret list --repo Shadowsong27/agentic-beacon
```

Should show:
```
PYPI_API_TOKEN  Updated 2026-XX-XX
```

## Important Notes

### First Upload Issue

⚠️ **For the FIRST upload**, you have two options:

**Option 1: Use "Entire account" scope**
- When creating the token, select "Scope: Entire account"
- This allows uploading any package
- After first upload, you can create a project-specific token

**Option 2: Manual first upload**
- Do the first upload manually: `cd libs/beacon && uv publish`
- After package exists on PyPI, create a project-specific token
- Update GitHub secret with the project-specific token

### Token Scopes

- **Entire account**: Can upload any package (less secure)
- **Project: agentic-beacon**: Can only upload to this specific package (more secure)
- **Recommendation**: Use "Entire account" for first upload, then switch to project-specific

### Security Best Practices

- ✅ Use project-specific tokens when possible
- ✅ Rotate tokens regularly
- ✅ Never commit tokens to git
- ✅ Use unique tokens for different purposes
- ❌ Don't share tokens
- ❌ Don't use the same token for multiple projects

## Testing (Optional)

If you want to test on TestPyPI first:

1. Go to https://test.pypi.org/manage/account/token/
2. Create a token (same process)
3. Add to GitHub:
   ```bash
   gh secret set TEST_PYPI_API_TOKEN --repo Shadowsong27/agentic-beacon
   ```

## After Setup

Once the token is set, you can:

1. **Automatic releases**: Push conventional commits to trigger release-please
2. **Manual releases**: Run `gh workflow run release-please.yml`
3. **Test publishing**: Run `gh workflow run publish-pypi.yml -f environment=test`

## Troubleshooting

### "Invalid credentials" error

- Verify secret exists: `gh secret list`
- Check token starts with `pypi-`
- Verify token hasn't expired
- Try creating a new token

### "Package does not exist" error

- For first upload, use "Entire account" scope
- Or do first manual upload: `cd libs/beacon && uv publish`

### Token not working

- Delete and recreate: `gh secret delete PYPI_API_TOKEN`
- Create new token on PyPI
- Set new secret: `gh secret set PYPI_API_TOKEN`

## Quick Commands

```bash
# View all secrets
gh secret list --repo Shadowsong27/agentic-beacon

# Set PyPI token
gh secret set PYPI_API_TOKEN --repo Shadowsong27/agentic-beacon

# Test workflow
gh workflow run publish-pypi.yml -f environment=test

# View workflow runs
gh run list --workflow=publish-pypi.yml
```

## Summary

**What you need to do:**

1. ✅ Create PyPI account
2. ✅ Generate API token (scope: "Entire account" for first upload)
3. ✅ Copy token (starts with `pypi-`)
4. ✅ Add to GitHub: `gh secret set PYPI_API_TOKEN`
5. ✅ Ready to publish!

**Token format example:**
```
pypi-AgEIcHlwaS5vcmcCJGFiY2RlZi0xMjM0LTU2NzgtYWJjZC1lZjEyMzQ1Njc4OTAA...
```

The token is long (200+ characters) and starts with `pypi-`.
