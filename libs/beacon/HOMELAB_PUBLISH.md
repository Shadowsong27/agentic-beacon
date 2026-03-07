# Publishing Beacon to Homelab PyPI

## Prerequisites

1. **uv installed** - Ensure you have uv installed in your homelab environment
2. **Python 3.12+** - Required for building and using beacon
3. **Homelab PyPI server** - Your private PyPI server should be running

## Build the Package

```bash
cd libs/beacon

# Build with uv
uv build

# This creates:
# - dist/beacon-0.1.0-py3-none-any.whl
# - dist/beacon-0.1.0.tar.gz
```

## Publish to Homelab PyPI

### Option 1: Using uv publish (Recommended)

```bash
cd libs/beacon

# Publish to your homelab PyPI
uv publish \
  --publish-url https://your-homelab-pypi.local/simple/ \
  --username your-username \
  --password your-password

# Or with token authentication:
uv publish \
  --publish-url https://your-homelab-pypi.local/simple/ \
  --token your-api-token
```

### Option 2: Using Environment Variables

Create a `.pypirc` file or set environment variables:

```bash
# In ~/.pypirc
[distutils]
index-servers =
    homelab

[homelab]
repository = https://your-homelab-pypi.local/simple/
username = your-username
password = your-password
```

Then publish:

```bash
cd libs/beacon
uv publish --index homelab
```

### Option 3: Using twine (Alternative)

```bash
cd libs/beacon

# Install twine in dev environment
uv pip install twine

# Upload to homelab PyPI
twine upload --repository-url https://your-homelab-pypi.local/simple/ dist/*
```

## Install from Homelab PyPI

Once published, users can install beacon from your homelab PyPI:

```bash
# Install from homelab PyPI
pip install beacon --index-url https://your-homelab-pypi.local/simple/

# Or with uv:
uv pip install beacon --index-url https://your-homelab-pypi.local/simple/

# Or add to requirements:
echo "beacon" >> requirements.txt
pip install -r requirements.txt --index-url https://your-homelab-pypi.local/simple/
```

## Verify Installation

```bash
# Check version
beacon --help

# Should show:
# Beacon - Guide your agents with distributed knowledge.
#
# Commands:
#   clean   Remove .opencode directory from project.
#   delta   Compare target installation with warehouse...
#   list    List available warehouse content.
#   setup   Setup warehouse content in project...
#   status  Show current warehouse installation status.
#   update  Update existing .opencode content...
```

## Upgrade Package

When you release a new version:

1. Update version in `pyproject.toml`
2. Rebuild: `uv build`
3. Republish: `uv publish --publish-url ...`

Users upgrade with:

```bash
pip install --upgrade beacon --index-url https://your-homelab-pypi.local/simple/
```

## Troubleshooting

### Build fails with Python version error

Make sure you're using Python 3.12+:

```bash
python --version  # Should be 3.12 or higher
uv python install 3.12  # Install Python 3.12 with uv
uv build --python 3.12  # Build with specific Python version
```

### Publish authentication fails

Check your credentials:

```bash
# Test connection
curl -u username:password https://your-homelab-pypi.local/simple/

# Or use token
curl -H "Authorization: Bearer your-token" https://your-homelab-pypi.local/simple/
```

### SSL certificate issues

If using self-signed certificates:

```bash
# Option 1: Add --no-verify-ssl (not recommended for production)
uv publish --publish-url ... --no-verify-ssl

# Option 2: Add cert to trusted store
pip install --cert /path/to/ca-bundle.crt beacon --index-url ...
```

## Next Steps

After testing in homelab:

1. Gather feedback from homelab users
2. Fix any issues
3. Increment version (e.g., 0.1.1, 0.2.0)
4. Rebuild and republish
5. When ready for public release:
   - `uv publish` (publishes to PyPI.org by default)
   - Or `twine upload dist/*` for PyPI

## Configuration Summary

**Package Name:** `beacon`  
**Version:** `0.1.0`  
**Python Required:** `>=3.12`  
**License:** MIT  
**Repository:** https://github.com/Shadowsong27/agentic-engineering-warehouse-template

**Installation:**
```bash
pip install beacon --index-url https://your-homelab-pypi.local/simple/
```

**Usage:**
```bash
beacon setup --all
beacon status
beacon delta
```
