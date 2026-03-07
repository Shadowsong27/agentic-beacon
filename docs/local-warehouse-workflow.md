# Local Warehouse Workflow Design

## Overview

This document describes the high-level workflow for using local warehouses with the Agentic Beacon CLI. The approach uses a **snapshot-based copy model** rather than symlinks, treating the warehouse like a "package registry" and project artifacts like `node_modules` - a versioned dependency that can be updated on demand.

## Architecture: The Three-Tier Model

```
Remote Warehouse (GitHub)
       ↓ git pull
Local Warehouse Clone (~/org-warehouse) ← User maintains with git
       ↓ abc download/setup (PURE COPY)
Project Artifacts (.agents/) ← Snapshot, can be locally modified
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

**With a pure copy**, they can safely edit `.agents/knowledge/lessons.md` locally, test it out, and then use the delta workflow to review local changes against the warehouse before deciding to push them upstream.

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
# Install all artifacts
abc setup --all

# Or selectively install
abc download context python
abc download skill deploy-production
```

**What happens:**
- CLI performs **pure copy** of artifacts into `my-project/.agents/`
- Creates a snapshot at the current warehouse state
- Developer adds `.agents/` to `.gitignore` (artifacts aren't duplicated in project's Git repo)

### Phase 4: Local Iteration Loop (Working with Agent)

The developer works on their project. Suppose the agent keeps making a specific mistake with a Python library:

1. Developer opens `my-project/.agents/knowledge/languages/python/lessons.md`
2. Adds a new guardrail instruction locally
3. Tests with agent
4. Because it's a pure copy, this local mutation is safe—doesn't affect other projects

**Key insight:** Local modifications are isolated to this project only.

### Phase 5: Upstream Contribution (Delta Workflow)

Once the developer confirms their new guardrail works, they check localized changes:

```bash
abc delta --warehouse ~/org-warehouse
```

**What happens:**
- CLI compares project `.agents/` against connected warehouse
- Highlights that `lessons.md` was modified locally
- Shows diff of changes

**Developer workflow:**
1. Review the delta output
2. Decide: keep local, contribute to warehouse, or discard
3. If contributing: manually copy changes to `~/org-warehouse/knowledge/languages/python/lessons.md`
4. Commit in warehouse: `cd ~/org-warehouse && git commit -am "Add Python library guardrail"`
5. Push to remote: `git push origin main`
6. Open PR for team review

### Phase 6: Syncing Updates (Refreshing Snapshot)

When another team member updates their local warehouse:

```bash
cd ~/org-warehouse
git pull origin main
```

Their local projects **don't change automatically**. When ready to adopt the newest standards:

```bash
cd ~/their-project
abc update
```

**What happens:**
- CLI detects if user made local changes in `.agents/`
- Warns: "You have local changes in .agents/, use abc delta to review before updating"
- If no conflicts or user confirms, overwrites `.agents/` with fresh copy from warehouse

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
- ✅ **Consistent paths**: Agents always read from `.agents/` in project root

## Command Summary

| Command | Purpose |
|---------|---------|
| `abc warehouse connect --path <path>` | Connect project to local warehouse |
| `abc setup --all` | Initial snapshot: copy all artifacts to project |
| `abc download <artifact>` | Copy specific artifact from warehouse |
| `abc update` | Refresh artifacts from warehouse (with change detection) |
| `abc delta` | Compare local changes against warehouse |
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
# Modified: .agents/knowledge/languages/python/lessons.md
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

**Last Updated:** 2026-03-08
