# {org_name} Agentic Engineering Warehouse

Centralized repository for coding standards, knowledge, and skills used by AI agents across {org_name}.

Under the current Agentic Beacon model, this warehouse clone is the **single write entrypoint** for every harness artifact on a developer's machine. Projects reference it via per-file symlinks under `.agentic-beacon/artifacts/`. See [single-warehouse-write-entrypoint](knowledge/decisions/single-warehouse-write-entrypoint.md) if this document is scaffolded with that decision.

## Quick Start

### For Developers

```bash
# 1. Install the Agentic Beacon CLI (once per machine; macOS/Linux only)
uv tool install agentic-beacon

# 2. Clone this warehouse locally (stays on disk; projects symlink into it)
git clone <this-repo-url> ~/path/to/this-warehouse

# 3. In your project, connect to this warehouse
cd ~/my-project
abc warehouse connect --path ~/path/to/this-warehouse

# 4. Create your artifact config and sync
abc setup             # creates .agentic-beacon/beacon.yaml
abc adopt             # select relevant warehouse artifacts
abc sync              # creates symlinks into the warehouse clone

# 5. (Optional) Install global agents from this warehouse
abc agents sync
```

### For Contributors

```bash
# Edit an artifact through any project's symlink (writes land in the warehouse working tree)
$EDITOR ~/my-project/.agentic-beacon/artifacts/knowledge/python/type-hints.md

# See what changed (scoped to your project's beacon.yaml)
abc warehouse status

# Commit and optionally push
abc warehouse contribute -m "python: clarify type hints" --push
```

Alternatively, edit files directly in the warehouse clone and commit with plain `git`.

After your changes are pushed, teammates pull the warehouse and the content is immediately visible through their existing project symlinks — no per-project `abc sync` required (unless `beacon.yaml` itself changed).

### Offline / Private Install

Download the bundle zip for your platform from the [Releases page](<releases-url>):

```bash
unzip agentic_beacon-X.Y.Z-bundle-<platform>.zip -d abc-bundle
uv tool install agentic-beacon --no-index --find-links ./abc-bundle/
```

## Structure

- **`contexts/`** — Boot instructions loaded by agents at session start
- **`knowledge/`** — Atomic decisions, lessons, and facts organized by scope
- **`skills/`** — Reusable workflows and procedures (agent slash commands)
- **`agents/`** — Global sub-agent profiles installed per-machine
- **`docs/`** — Warehouse documentation and contribution guides

## CLI Reference

| Command | Description |
|---------|-------------|
| `abc warehouse connect --path <path>` | Connect a project to this warehouse clone |
| `abc setup` | Create `beacon.yaml` for a project |
| `abc sync` | Create symlinks into the warehouse clone for every declared artifact |
| `abc sync --dry-run` | Preview the sync operations without touching the filesystem |
| `abc agents sync` | Link every agent definition from the warehouse into global tool directories |
| `abc warehouse status` | Show uncommitted warehouse edits (scoped by `beacon.yaml`) |
| `abc warehouse contribute -m "…" [--push]` | Commit warehouse edits and optionally push |

**Platform support:** macOS and Linux only. Windows is not supported by `abc sync`.

## Documentation

- [Contribution Guide](./docs/contribution-guide.md) — How to add content

## Maintenance

This warehouse is maintained by {org_name}'s Platform Team.

- **Review Frequency:** Quarterly
- **Questions:** Contact platform-team@example.com
- **Issues:** Open an issue in this repository
