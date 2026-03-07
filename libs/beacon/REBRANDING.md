# Agentic Beacon (abc) - Rebranding Complete

## 🎯 New Branding

### Package Name
- **Old:** `beacon`
- **New:** `agentic-beacon`

### CLI Command
- **Old:** `beacon`
- **New:** `abc` (Agentic Beacon CLI)

### Rationale
- ✅ `abc` is shorter and more memorable
- ✅ `agentic-beacon` makes the package purpose clearer
- ✅ Better discoverability on PyPI
- ✅ More distinctive branding

## 📦 Installation

```bash
# Homelab PyPI
pip install agentic-beacon --index-url https://your-homelab-pypi.local/simple/

# Public PyPI (when published)
pip install agentic-beacon
```

## 🚀 Commands

All commands now use `abc` instead of `beacon`:

| Command | Description |
|---------|-------------|
| `abc init` | Initialize a new warehouse repository |
| `abc list` | List available warehouse content |
| `abc setup` | Install content to `.opencode/` |
| `abc status` | Show installed content |
| `abc delta` | Compare with warehouse |
| `abc update` | Sync from warehouse |
| `abc clean` | Remove installation |

## 📝 Examples

```bash
# Initialize warehouse
abc init my-warehouse \
  --org "Acme Corp" \
  --languages python,typescript \
  --domains data-platform

# List content
abc list --warehouse ~/warehouse

# Setup in project
abc setup --warehouse ~/warehouse --all

# Check status
abc status

# Find changes
abc delta --warehouse ~/warehouse

# Update
abc update --warehouse ~/warehouse

# Clean
abc clean
```

## 🔄 Migration Guide

If you were using the old `beacon` command:

### Update Installation

```bash
# Uninstall old version
pip uninstall beacon

# Install new version
pip install agentic-beacon 
```

### Update Commands

Simply replace `beacon` with `abc` in all your commands and scripts:

```bash
# Old
beacon init my-warehouse
beacon setup --all
beacon status

# New
abc init my-warehouse
abc setup --all
abc status
```

### Update Documentation

Update any internal documentation or scripts that reference:
- Package name: `beacon` → `agentic-beacon`
- Command: `beacon` → `abc`

## 📊 What Changed

### Files Updated
- `libs/beacon/pyproject.toml` - Package name, CLI entry point, URLs
- `libs/beacon/src/beacon/cli.py` - Help text, examples
- `libs/beacon/src/beacon/initializer.py` - Generated file references
- `README.md` - All command examples and branding
- Documentation guides - Command references

### GitHub Repository
- Repository URL now points to: `https://github.com/Shadowsong27/agentic-beacon`
- Update your repository name on GitHub to match (Settings → Repository name)

## 🎨 Branding

**Full Name:** Agentic Beacon  
**CLI Command:** abc  
**Tagline:** "Guide your agents with distributed knowledge"  
**Purpose:** Distribute knowledge contexts and skills for AI-assisted development teams

## 🚢 Deployment

### Build

```bash
cd libs/beacon
uv build
```

### Publish to Homelab

```bash
uv publish \
  --publish-url https://your-homelab-pypi.local/simple/ \
  --token your-token
```

### Publish to PyPI (when ready)

```bash
uv publish
```

## ✅ Testing

All commands tested and working:

```bash
$ abc --help
Usage: abc [OPTIONS] COMMAND [ARGS]...

  Agentic Beacon CLI (abc) - Guide your agents with distributed knowledge.

$ abc init test-warehouse --org "Test" --languages python --no-interactive
✓ Warehouse initialized successfully!

$ abc list --warehouse test-warehouse
# Shows contexts, knowledge, skills

$ abc setup --warehouse test-warehouse --all
✓ Setup complete!

$ abc status
# Shows installation details

$ abc delta
# Compares with warehouse

$ abc update
✓ Update complete!

$ abc clean
✓ Removed .opencode/
```

## 📋 Next Steps

1. **Update GitHub repo name:** `agentic-engineering-warehouse-template` → `agentic-beacon`
2. **Deploy to homelab:** Test with your team
3. **Gather feedback:** Use for 2-4 weeks internally
4. **Public release:** When ready, deploy to public PyPI

## 🎉 Summary

**Package:** `agentic-beacon`  
**Command:** `abc`  
**Version:** 0.2.0  
**Status:** ✅ Ready for deployment

All functionality preserved, just with better branding and a more memorable CLI command!
