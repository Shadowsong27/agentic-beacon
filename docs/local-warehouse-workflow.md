# Local Warehouse Workflow Design

## Overview

This document describes the high-level workflow for using local warehouses with the Agentic Beacon CLI. The approach uses a **snapshot-based copy model** rather than symlinks, treating the warehouse like a "package registry" and project artifacts like `node_modules` - a versioned dependency that can be updated on demand.

## Architecture: The Three-Tier Model

```
Remote Warehouse (GitHub)
       ↓ git pull
Local Warehouse Clone (~/org-warehouse) ← User maintains with git
       ↓ abc sync (PURE COPY)
Project Artifacts (.agentic-beacon/artifacts/) ← Snapshot, can be locally modified
       ↓ abc delta (COMPARE & CONTRIBUTE)
Back to Local Warehouse ← User commits and pushes
```

## Why Pure Copy Over Symlinks

### 1. Agent Sandboxing / File Resolution
Many AI agents (Cursor, OpenCode, Docker-based agents) operate in restricted workspaces. If an agent tries to read a symlink pointing outside the project root (e.g., `~/org-warehouse/knowledge`), it will often fail due to:
- Permission constraints
- Relative path traversal limits
- Docker volume mount boundaries
- Remote development environment restrictions

**Pure copies guarantee files are physically present** inside the project where agents expect them.

### 2. Project Stability (Versioning)
You want deterministic project behavior. If a developer pulls a breaking change into their local warehouse clone, a symlink would instantly apply those changes to all local projects. If the new knowledge pattern is flawed, it breaks all projects at once.

**A pure copy acts as a snapshot**, meaning a project only gets new knowledge when the developer explicitly runs an update command.

### 3. Local Experimentation (The "Delta" Loop)
A developer might want to tweak a knowledge file to see if the agent writes better code. If it's a symlink, they are directly editing their central warehouse repo.

**With a pure copy**, they can safely edit `.agentic-beacon/artifacts/knowledge/lessons.md` locally, test it out, and then use the delta workflow to review local changes against the warehouse before deciding to push them upstream.

### 4. Cross-Platform Compatibility
Symlinks on Windows can still be problematic (often requiring Developer Mode or admin privileges). **Pure file copying is universally safe.**

## The Recommended User Workflow

### Phase 1: Global State (The Warehouse)

The user maintains a local clone of the remote Git warehouse:

```bash
# Clone the organizational warehouse once
git clone https://github.com/my-org/eng-warehouse.git ~/org-warehouse
```

This repository tracks the "main" branch of the team's standard artifacts (contexts, knowledge, skills).

### Phase 2: Connecting to Local Warehouse

When starting work on a project, connect it to the local warehouse:

```bash
cd ~/my-project

# Connect to local warehouse (interactive or parameter-based)
abc warehouse connect --path ~/org-warehouse
```

**What happens:**
- CLI validates warehouse structure
- Stores connection configuration in `.agentic-beacon/config.toml` (gitignored)
- Project now knows where to sync artifacts from

### Phase 3: Installing Artifacts (Snapshotting)

Download artifacts from the connected warehouse:

```bash
# Configure which artifacts you want
abc setup --manual
# Edit .agentic-beacon/beacon.yaml to declare contexts, knowledge, and skills

# Sync artifacts from warehouse
abc sync
```

**What happens:**
- CLI performs **pure copy** of declared artifacts into `my-project/.agentic-beacon/artifacts/`
- Creates a snapshot at the current warehouse state
- `.agentic-beacon/artifacts/` is gitignored (artifacts aren't duplicated in project's Git repo)

### Phase 4: Local Iteration Loop (Working with Agent)

The developer works on their project. Suppose the agent keeps making a specific mistake with a Python library:

1. Developer opens `my-project/.agentic-beacon/artifacts/knowledge/languages/python/lessons.md`
2. Adds a new guardrail instruction locally
3. Tests with agent
4. Because it's a pure copy, this local mutation is safe—doesn't affect other projects

**Key insight:** Local modifications are isolated to this project only.

### Phase 5: Upstream Contribution (Delta Workflow)

Once the developer confirms their new guardrail works, they check localized changes:

```bash
abc delta
```

**What happens:**
- CLI compares project `.agentic-beacon/artifacts/` against connected warehouse
- Highlights that `lessons.md` was modified locally
- Shows diff of changes

**Developer workflow:**
1. Review the delta output
2. Decide: keep local, contribute to warehouse, or discard
3. If contributing: run `abc contribute` — automatically creates a branch, commits, pushes, and opens a PR

### Phase 6: Discovering and Adopting New Artifacts

When another team member contributes a new artifact to the warehouse (via `abc contribute`), you'll discover it during your next sync.

```bash
cd ~/org-warehouse
git pull origin main

cd ~/their-project
abc sync
```

If new artifacts were added since your last sync, you'll see a notification at the end of sync output:

```
✓ Sync complete
  Copied: 1 files
  Unchanged: 5 files

2 new artifact(s) available -- run abc adopt to review
```

Run `abc adopt` to open an interactive TUI and choose which new artifacts to add to your `beacon.yaml`:

```bash
abc adopt
```

**What happens:**
- Shows all warehouse artifacts added since your last sync that aren't yet in `beacon.yaml`
- Categorized checkboxes: contexts, skills, knowledge
- Press `a` (select all), `n` (deselect all), `Enter` (confirm), `Escape`/`q` (cancel)
- On confirm: selected artifacts are appended to `beacon.yaml` and immediately synced + wired

**Useful flags:**

```bash
abc adopt --dry-run   # Preview what's available without changing anything
abc adopt --all       # Show everything in the warehouse you haven't adopted yet
```

### Phase 7: Syncing Updates to Existing Artifacts (Refreshing Snapshot)

To refresh already-adopted artifacts that have been updated in the warehouse:

```bash
cd ~/their-project
abc sync
```

**What happens:**
- `abc sync` re-syncs all artifacts declared in `beacon.yaml`, overwriting stale local copies with the latest from the warehouse
- Any local modifications to artifacts will be lost — use `abc delta` first to review and save changes worth keeping

## Benefits of This Workflow

### For Individual Developers
- ✅ **Safe experimentation**: Edit artifacts locally without affecting other projects
- ✅ **Deterministic builds**: Project behavior doesn't change until you explicitly update
- ✅ **Works everywhere**: No symlink issues across platforms or agent environments

### For Teams
- ✅ **Controlled rollout**: Teams update warehouse on their own schedule
- ✅ **Contribution workflow**: Delta-based review before pushing changes upstream
- ✅ **Version pinning**: Projects can stay on known-good warehouse state

### For Agent Compatibility
- ✅ **Physical files**: All artifacts present in project directory
- ✅ **No path resolution issues**: Works in Docker, remote environments, sandboxes
- ✅ **Consistent paths**: Agents always read from `.agentic-beacon/artifacts/` in project root

## Command Summary

| Command | Purpose |
|---------|---------|
| `abc warehouse connect --path <path>` | Connect project to local warehouse |
| `abc setup --manual` | Create `beacon.yaml` to declare which artifacts to sync |
| `abc sync` | Snapshot declared artifacts from warehouse; notifies of new unadopted artifacts |
| `abc adopt` | Interactively adopt new warehouse artifacts into `beacon.yaml` |
| `abc adopt --dry-run` | Preview adoptable artifacts without modifying anything |
| `abc adopt --all` | Show every warehouse artifact not yet in `beacon.yaml` |
| `abc update` | Refresh artifacts from warehouse (force-overwrites local copies) |
| `abc delta` | Compare local artifact changes against warehouse |
| `git pull` (in warehouse) | Update local warehouse from remote |

## The Node_modules Analogy

Think of the warehouse as **npm registry**:
- Remote warehouse = npmjs.com (central source)
- Local warehouse = npm cache (~/.npm)
- Project artifacts = node_modules (local copy)
- `abc update` = npm install (refresh dependencies)
- `abc delta` = git diff (see what changed locally)

Just like you don't symlink to node_modules from a central location, you don't symlink to warehouse artifacts. Each project gets its own snapshot.

## Future Enhancements

### Automatic Change Detection
Could track checksums/timestamps to detect local modifications automatically:
```bash
abc status
# Output:
# Modified: .agentic-beacon/artifacts/knowledge/languages/python/lessons.md
# Run 'abc delta' to review changes
```

### Warehouse Version Locking
Could add `.agentic-beacon/lock.toml` to pin warehouse version:
```toml
[warehouse]
commit = "abc123def456"  # Git commit SHA
```

### Upstream Push Helper
Could automate the contribution workflow:
```bash
abc push --message "Add Python guardrail"
# Creates branch in warehouse, commits changes, opens PR
```

---

**Last Updated:** 2026-03-10
