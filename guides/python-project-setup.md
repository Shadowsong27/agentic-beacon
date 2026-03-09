# Python Project Setup

This guide shows how to configure Agentic Beacon for a Python project. The specific paths in `beacon.yaml` will depend on how your warehouse is organized — these examples are illustrative, not prescriptive.

## Prerequisites

- A warehouse exists and is accessible (see [Creating a Warehouse](./warehouse-creation.md))
- You've installed Agentic Beacon: `pip install agentic-beacon`

## Initial Setup

```bash
cd my-python-project
abc warehouse connect --path ~/team-warehouse
abc setup --manual
```

This creates `.agentic-beacon/beacon.yaml` with an empty template.

---

## Configuring beacon.yaml

Edit `.agentic-beacon/beacon.yaml` to declare which artifacts your Python project needs. The paths are relative to your warehouse root — match them to however your warehouse is actually organized.

```yaml
# .agentic-beacon/beacon.yaml

artifacts:
  knowledge:
    # Pull specific files you know you need
    - knowledge/decisions/coding-standards.md
    - knowledge/decisions/testing-strategy.md

    # Or pull an entire subtree with a glob
    - knowledge/python/**/*.md

  skills:
    - skills/code-review/**/*
    - skills/generate-tests/**/*

  contexts:
    - contexts/global.md
    - contexts/backend/AGENTS.md
```

Then sync:

```bash
abc sync
```

---

## Typical Python Artifact Needs

Python projects commonly benefit from team knowledge around:

- **Type annotation standards** — which patterns to use, what to avoid
- **Testing approach** — pytest conventions, fixture patterns, coverage expectations
- **Async patterns** — if using async/await throughout
- **Framework conventions** — how your team uses FastAPI, SQLAlchemy, Pydantic, etc.
- **Error handling standards** — exception hierarchy, logging patterns
- **Dependency management** — how you use uv, pip, virtual environments

These would live as knowledge files in your warehouse at paths your team chooses. Your `beacon.yaml` pulls whichever ones apply to the project.

---

## Selective Artifact Loading

Not every Python project needs the same things. Pull only what's relevant.

**A focused microservice:**
```yaml
artifacts:
  knowledge:
    - knowledge/decisions/coding-standards.md
    - knowledge/fastapi-patterns.md
    - knowledge/testing/pytest-guide.md
  skills:
    - skills/code-review/**/*
  contexts:
    - contexts/global.md
```

**A data pipeline:**
```yaml
artifacts:
  knowledge:
    - knowledge/decisions/coding-standards.md
    - knowledge/data/pipeline-patterns.md
    - knowledge/data/testing-strategy.md
  skills:
    - skills/code-review/**/*
  contexts:
    - contexts/global.md
    - contexts/data-team/AGENTS.md
```

**A minimal setup for a new project:**
```yaml
artifacts:
  knowledge:
    - knowledge/decisions/coding-standards.md
  skills: []
  contexts:
    - contexts/global.md
```

Start minimal and add artifacts as you identify what the agent needs.

---

## Project-Specific Local Knowledge

You can keep project-specific knowledge alongside synced artifacts. Create a local directory that you commit to your project repo:

```bash
mkdir -p .agentic-beacon/local-knowledge
echo "# Rate Limiting Strategy\n\nThis service uses..." > .agentic-beacon/local-knowledge/rate-limiting.md
```

This is project-specific content that doesn't belong in the shared warehouse:
- ✅ Commit to git (it's project-specific)
- ✅ Lives alongside synced artifacts
- ✅ Not affected by `abc sync` or `abc clean`

---

## Updating Artifacts

When your team updates knowledge in the warehouse:

```bash
cd ~/team-warehouse && git pull
cd my-python-project && abc sync
```

Unchanged files are skipped. Only updated files are re-copied.

---

## Verifying the Setup

Check what was synced and that contexts/skills are in place:

```bash
abc status
```

Test that the agent is using the artifacts by asking it a question that your knowledge artifacts should inform — for example, "How should I write tests for this project?" — and see if the answer reflects your team's standards.

---

## Integration with Dev Tools

### Pre-commit hook

Keep artifacts in sync automatically:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: sync-beacon-artifacts
        name: Sync Beacon Artifacts
        entry: abc sync
        language: system
        pass_filenames: false
```

### CI/CD

```yaml
# .github/workflows/ci.yml
- name: Setup Beacon Artifacts
  run: |
    pip install agentic-beacon
    abc warehouse connect --path ./warehouse
    abc sync
```

---

## Troubleshooting

### Pattern matches nothing

```
Warning: No files matched pattern: knowledge/python/fastapi.md
```

Check that the path actually exists in your warehouse:

```bash
ls /path/to/warehouse/knowledge/
```

Adjust the pattern to match the real structure. See [Advanced Patterns](./advanced-patterns.md) for glob syntax.

### Too many artifacts synced

Use a more specific pattern:

```yaml
# Before: syncs everything under knowledge/
- knowledge/**/*.md

# After: only the files you need
- knowledge/decisions/coding-standards.md
- knowledge/testing/**/*.md
```

### Conflicting local edits

Use `--preserve` to protect local modifications:

```bash
abc sync --preserve
```

Use `abc delta` to review what differs before deciding whether to keep or discard local changes.

---

## Next Steps

- **[Advanced Patterns](./advanced-patterns.md)** — Glob syntax, sync flags, delta workflow
- **[Creating Skills](./creating-skills.md)** — Build Python-specific skills for your team
- **[Team Collaboration](./team-collaboration.md)** — Share configurations across the team
- **[beacon.yaml Reference](./beacon-yaml-reference.md)** — Full configuration schema

---

**Related Guides:**
- [Getting Started](./getting-started.md)
- [Team Collaboration](./team-collaboration.md)
- [beacon.yaml Reference](./beacon-yaml-reference.md)
