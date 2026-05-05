# Team Collaboration

This guide covers how teams share a warehouse, stay in sync, and manage the contribution workflow at scale.

## The Collaboration Model

| Role | Artifact |
|------|---------|
| **Warehouse** | Your team's shared registry — one git repo |
| **`beacon.yaml`** | Each project's context and skill dependencies |
| **Artifacts** | Synced to each developer's local machine |

The warehouse is the single source of truth. Projects pull from it; improvements flow back to it.

---

## Setting Up Team Collaboration

### 1. Create and push a warehouse

```bash
abc warehouse init team-warehouse
cd team-warehouse

# Add initial content
mkdir -p knowledge/languages/python
mkdir -p contexts/teams/backend
mkdir -p skills/code-review

git init
git add .
git commit -m "Initial team warehouse"
git remote add origin git@github.com:yourorg/team-warehouse.git
git push -u origin main
```

### 2. Team members connect

Each team member clones the warehouse and connects their projects:

```bash
# Clone warehouse
git clone git@github.com:yourorg/team-warehouse.git ~/team-warehouse

# In each project
cd my-project
abc warehouse connect --path ~/team-warehouse
abc adopt      # select artifacts interactively
abc sync       # sync and wire
```

**Tip:** Add to your team onboarding checklist:

```markdown
## Developer Setup
- [ ] Clone warehouse: `git clone git@github.com:yourorg/team-warehouse.git ~/team-warehouse`
- [ ] In each project: `abc warehouse connect --path ~/team-warehouse`
- [ ] Select artifacts: `abc adopt`
- [ ] Sync artifacts: `abc sync`
```

---

## Workflow Patterns

### Pattern 1: Standardized Project Templates

Create example `beacon.yaml` files in the warehouse for common project types:

```yaml
# team-warehouse/examples/beacon-python-api.yaml
artifacts:
  skills:
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/teams/backend/AGENTS.md
```

New projects copy the template:

```bash
cd new-api-project
abc warehouse connect --path ~/team-warehouse
abc setup
cp ~/team-warehouse/examples/beacon-python-api.yaml .agentic-beacon/beacon.yaml
abc sync
```

Knowledge files referenced by those contexts and skills are auto-derived — no manual knowledge configuration needed.

### Pattern 2: Progressive Artifact Adoption

Start minimal, grow as the warehouse grows:

**Sprint 1 — Start minimal:**
```yaml
artifacts:
  skills: []
  contexts:
    - contexts/teams/backend/AGENTS.md
```

**After warehouse grows:**
```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
# → "2 new artifact(s) available — run abc adopt to review"
abc adopt
# → TUI: select code-review skill, generate-tests skill → Enter
```

### Pattern 3: Team-Specific Contexts

Organize contexts by team structure:

```
contexts/
├── teams/
│   ├── backend/AGENTS.md          # backend team standards
│   ├── frontend/AGENTS.md         # frontend team standards
│   └── platform/AGENTS.md         # platform team standards
└── projects/
    ├── customer-portal/AGENTS.md
    └── internal-tools/AGENTS.md
```

Backend project `beacon.yaml`:
```yaml
artifacts:
  skills: []
  contexts:
    - contexts/teams/backend/AGENTS.md
    - contexts/projects/customer-portal/AGENTS.md
```

Frontend project `beacon.yaml`:
```yaml
artifacts:
  skills: []
  contexts:
    - contexts/teams/frontend/AGENTS.md
    - contexts/projects/customer-portal/AGENTS.md
```

---

## Maintaining the Warehouse

### Adding new knowledge

Knowledge is auto-derived from markdown links. When you add a knowledge file to the warehouse, link to it from a context or skill and it will be synced automatically:

```bash
cd ~/team-warehouse
cat > knowledge/best-practices/error-handling.md << 'EOF'
# Error Handling Best Practices
...
EOF

# Add a reference in the backend context
echo "See [Error Handling](knowledge/best-practices/error-handling.md) for guidelines." >> contexts/teams/backend/AGENTS.md

git add .
git commit -m "docs: add error handling best practices"
git push
```

Team members get the new knowledge on their next sync:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

The resolver finds the `knowledge/best-practices/error-handling.md` link in the adopted context and syncs it automatically.

### Updating existing artifacts

```bash
cd ~/team-warehouse
vim knowledge/languages/python/type-hints.md

git add knowledge/languages/python/type-hints.md
git commit -m "docs: update type hints guide with Python 3.12 features"
git push
```

Team members get the update on their next sync:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

---

## Team Coordination

### Weekly warehouse reviews

1. Review PRs from team members
2. Discuss patterns that are working well
3. Prune outdated or deprecated artifacts
4. Update example `beacon.yaml` files

### Regular maintenance schedule

- **Monthly:** Review and prune outdated artifacts; remove dead markdown links
- **Quarterly:** Major version tags with changelogs
- **Ad-hoc:** Quick additions for new patterns

---

## Handling Conflicts

### Team standard changes

When a shared artifact is updated, sync picks up the latest:

```bash
# Before sync, review warehouse changes
abc warehouse status

# Sync
abc sync
```

### Multiple warehouse versions

For legacy projects that need an older warehouse state, use git tags:

```bash
cd ~/team-warehouse
git checkout v1-stable
```

---

## Multi-Repository Organizations

For large organizations, a hub-and-spoke model works well:

```
org-wide-warehouse/          # Org-wide standards
├── knowledge/security/
└── contexts/organization/

backend-team-warehouse/      # Team-specific standards
├── knowledge/languages/python/
└── contexts/teams/backend/
```

!!! note
    Agentic Beacon currently supports one warehouse per project. For multi-warehouse setups, merge warehouse content or use git submodules.

---

## Best Practices

1. **Clear ownership** — assign maintainers to warehouse sections (e.g., Python guild owns `knowledge/languages/python/`)
2. **Use frontmatter** — every skill's `SKILL.md` must declare `requires: { contexts: [...] }`
3. **Link to knowledge** — knowledge files only sync when referenced by a markdown link from an adopted context or skill
4. **Use semantic versioning** — tag stable warehouse releases: `v1.0.0`

---

## Next Steps

- **[Creating a Warehouse](warehouse-creation.md)** — detailed warehouse setup
- **[Contributing Back](contributing-back.md)** — getting improvements back to the warehouse
- **[Advanced Patterns](advanced-patterns.md)** — complex configurations
