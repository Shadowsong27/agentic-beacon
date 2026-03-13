# Your Organization Agentic Engineering Warehouse

Centralized repository for coding standards, knowledge, and skills used by AI agents across Your Organization.

## Quick Start

### For Developers

```bash
# 1. Install the Agentic Beacon CLI (once per machine)
uv tool install agentic-beacon

# 2. In your project, connect to this warehouse
cd ~/my-project
abc warehouse connect --path ~/path/to/this-warehouse

# 3. Create your artifact config and sync
abc setup --manual   # then edit .agentic-beacon/beacon.yaml
abc sync

# 4. (Optional) Register skills as agent slash commands
abc skill install --all
```

### For Contributors

```bash
# Clone warehouse
git clone <this-repo-url>

# Make changes
# - Add contexts, knowledge, or skills
# - Follow the contribution guide in docs/

# Submit PR

# After your changes are merged, teammates can pull them in with:
abc update
```

### Offline / Private Install

Download the bundle zip for your platform from the [Releases page](<releases-url>):

```bash
unzip agentic_beacon-X.Y.Z-bundle-<platform>.zip -d abc-bundle
uv tool install agentic-beacon --no-index --find-links ./abc-bundle/
```

## Structure

- **`contexts/`** - Boot instructions loaded by agents at session start
- **`knowledge/`** - Atomic decisions, lessons, and facts organized by scope
- **`skills/`** - Reusable workflows and procedures (agent slash commands)
- **`docs/`** - Warehouse documentation and contribution guides

## CLI Reference

| Command | Description |
|---------|-------------|
| `abc warehouse connect` | Connect a project to this warehouse |
| `abc setup` | Create `beacon.yaml` for a project |
| `abc sync` | Sync declared artifacts to the project |
| `abc skill install` | Register synced skills as agent slash commands |
| `abc list` | Show available content in the warehouse |
| `abc status` | Show connection and sync status |
| `abc delta` | Find local changes not yet contributed back |
| `abc contribute` | Copy local improvements back to the warehouse |
| `abc update` | Re-sync and overwrite local artifacts from warehouse |
| `abc clean` | Remove synced artifacts from the project |

## Documentation

- [Contribution Guide](./docs/contribution-guide.md) - How to add content

## Maintenance

This warehouse is maintained by Your Organization's Platform Team.

- **Review Frequency:** Quarterly
- **Questions:** Contact platform-team@example.com
- **Issues:** Open an issue in this repository
