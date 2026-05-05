# Team Collaboration with Agentic Beacon

This guide shows how teams can collaborate using Agentic Beacon to share agent configurations and maintain consistency across projects.

## The Collaboration Model

Think of it like npm for teams:
- **Warehouse** = Your team's shared registry
- **beacon.yaml** = Each project's dependencies
- **Artifacts** = Synced to each developer's machine

## Setting Up Team Collaboration

### 1. Create a Team Warehouse

Set up a central warehouse repository that your team maintains:

```bash
# Initialize warehouse structure
abc warehouse init team-warehouse
cd team-warehouse

# Populate with team standards
mkdir -p knowledge/languages/python
mkdir -p contexts/teams/backend
mkdir -p skills/code-review
```

**Warehouse structure:**
```
team-warehouse/
├── knowledge/
│   ├── languages/
│   │   ├── python/
│   │   └── go/
│   ├── best-practices/
│   └── infrastructure/
├── skills/
│   ├── code-review/
│   ├── testing/
│   └── deployment/
├── contexts/
│   ├── teams/
│   │   ├── backend/
│   │   ├── platform/
│   │   └── devops/
│   └── projects/
├── docs/
│   └── README.md
└── README.md
```

### 2. Version Control Your Warehouse

```bash
cd team-warehouse
git init
git add .
git commit -m "Initial team warehouse"
git remote add origin git@github.com:yourorg/team-warehouse.git
git push -u origin main
```

**What to commit:**
- ✅ All knowledge artifacts
- ✅ All skills
- ✅ All contexts
- ✅ README and documentation
- ✅ Example beacon.yaml files

### 3. Team Members Connect

Each team member clones and connects to the warehouse:

```bash
# Clone team warehouse
git clone git@github.com:yourorg/team-warehouse.git ~/team-warehouse

# In each project
cd my-project
abc warehouse connect --path ~/team-warehouse
```

**Pro tip:** Add to team onboarding checklist:
```markdown
## Developer Setup Checklist
- [ ] Clone team warehouse: `git clone git@github.com:yourorg/team-warehouse.git ~/team-warehouse`
- [ ] Connect project: `abc warehouse connect --path ~/team-warehouse`
- [ ] Sync artifacts: `abc sync`
```

## Workflow Patterns

### Pattern 1: Standardized Project Templates

Create example beacon.yaml files for common project types:

**team-warehouse/examples/beacon.yaml.python-api**
```yaml
artifacts:
    - languages/python/type-hints.md
    - languages/python/fastapi/**/*.md
    - languages/python/pytest/**/*.md
    - best-practices/api-design.md
    - infrastructure/docker-python.md

  skills:
    - python/code-review
    - python/generate-unit-tests

  contexts:
    - teams/backend/AGENTS.md
    - projects/api-services/standards.md
```

**Usage:**
```bash
# New team member starting Python API project
cd new-api-project
abc warehouse connect --path ~/team-warehouse
abc setup
cp ~/team-warehouse/examples/beacon.yaml.python-api .agentic-beacon/beacon.yaml
abc sync
```

### Pattern 2: Progressive Artifact Adoption

Start minimal, grow as needed. Use `abc adopt` to discover and add new artifacts as the warehouse grows — no manual `beacon.yaml` editing required.

**Sprint 1 - Start minimal:**
```yaml
artifacts:
    - languages/python/type-hints.md
    - best-practices/code-review.md

  skills: []

  contexts:
    - teams/backend/AGENTS.md
```

**Sprint 3 - Discover what's new:**
```bash
# After warehouse has grown with new testing artifacts
abc sync
# → "2 new artifact(s) available -- run abc adopt to review"

abc adopt
# → TUI: check pytest guide, tdd-workflow, generate-unit-tests skill → Enter
```

The new artifacts are appended to `beacon.yaml` automatically and synced immediately.

### Pattern 3: Team-Specific Contexts

Organize contexts by team structure:

```
contexts/
├── teams/
│   ├── backend/
│   │   └── AGENTS.md          # Backend team standards
│   ├── frontend/
│   │   └── AGENTS.md          # Frontend team standards
│   ├── platform/
│   │   └── AGENTS.md          # Platform team standards
│   └── data/
│       └── AGENTS.md          # Data team standards
└── projects/
    ├── customer-portal/
    │   └── AGENTS.md          # Project-specific context
    └── internal-tools/
        └── AGENTS.md
```

**Backend project beacon.yaml:**
```yaml
artifacts:
  contexts:
    - teams/backend/AGENTS.md
    - projects/customer-portal/AGENTS.md
```

**Frontend project beacon.yaml:**
```yaml
artifacts:
  contexts:
    - teams/frontend/AGENTS.md
    - projects/customer-portal/AGENTS.md
```

## Maintaining the Warehouse

### Adding New Knowledge

When the team learns something new:

```bash
cd ~/team-warehouse

# Add new best practice
cat > knowledge/best-practices/error-handling.md << 'EOF'
# Error Handling Best Practices

## Standard Error Response Format
...
EOF

# Commit and push
git add knowledge/best-practices/error-handling.md
git commit -m "Add error handling best practices"
git push
```

Team members discover and adopt it:

```bash
cd ~/team-warehouse
git pull

# In each project
cd my-project
abc sync
# Output: "1 new artifact(s) available -- run abc adopt to review"

abc adopt
# Opens TUI — select the new artifact, press Enter to adopt
```

Once adopted, `abc sync` will keep the artifact up to date on future runs.

If you prefer to review before committing, use `--dry-run`:

```bash
abc adopt --dry-run
```

### Updating Existing Knowledge

```bash
cd ~/team-warehouse
vim knowledge/languages/python/type-hints.md

git add knowledge/languages/python/type-hints.md
git commit -m "Update type hints guide with Python 3.12 features"
git push
```

Team members get updates (for artifacts already in their `beacon.yaml`):

```bash
cd ~/team-warehouse
git pull

cd my-project
abc sync  # Re-syncs changed files automatically
```

Artifacts not yet adopted won't be pulled by `abc sync` — use `abc adopt` to add them first.

## Team Coordination

### Weekly Warehouse Reviews

Schedule regular warehouse reviews:

1. **Review PRs** - Team members propose new artifacts
2. **Discuss patterns** - Share what's working
3. **Prune outdated** - Remove deprecated knowledge
4. **Update examples** - Keep beacon.yaml examples current

### Warehouse PR Template

```markdown
## New Artifact Proposal

**Type:** Knowledge / Skill / Context

**Location:** `knowledge/languages/python/pydantic-v2.md`

**Purpose:** Document Pydantic v2 migration patterns

**Affects:** All Python projects using Pydantic

**Example beacon.yaml:**
```yaml
  - languages/python/pydantic-v2.md
```

**Testing:**
- [ ] Used in at least one project
- [ ] Team review completed
- [ ] Examples validated

**Migration:**
- Existing projects should add to beacon.yaml and sync
```

## Handling Conflicts

### Scenario 1: Team Standard Changes

**Problem:** Team updates a standard, but some projects have local modifications.

**Solution:**
1. Warehouse PR includes migration guide
2. Projects sync when ready
3. Use git to track what changed

```bash
# Before sync
cp .agentic-beacon/artifacts/contexts/teams/backend/AGENTS.md /tmp/old-agents.md

# Sync
abc sync

# Review changes
diff /tmp/old-agents.md .agentic-beacon/artifacts/contexts/teams/backend/AGENTS.md
```

### Scenario 2: Multiple Warehouse Versions

**Problem:** Different projects need different warehouse versions.

**Solution:** Use git branches or tags:

```bash
# Main projects use main
abc warehouse connect --path ~/team-warehouse

# Legacy project uses v1
cd ~/team-warehouse
git checkout v1-stable

cd legacy-project
abc warehouse connect --path ~/team-warehouse
```

### Scenario 3: Project-Specific Overrides

**Problem:** Project needs team context plus local modifications.

**Solution:** Layer local contexts:

```yaml
artifacts:
  contexts:
    - teams/backend/AGENTS.md  # Team standards (synced)
    # Local context stored in project repo
    # .agentic-beacon/local-contexts/PROJECT.md
```

Create local context:
```bash
mkdir -p .agentic-beacon/local-contexts
cat > .agentic-beacon/local-contexts/PROJECT.md << 'EOF'
# Project-Specific Context

Extends backend team standards with project specifics.
EOF

git add .agentic-beacon/local-contexts/
git commit -m "Add project-specific context"
```

## Multi-Repository Organizations

For large organizations with multiple warehouses:

### Hub and Spoke Model

```
org-wide-warehouse/          # Org-wide standards
├── knowledge/
│   └── security/
│       └── auth-standards.md
└── contexts/
    └── organization/
        └── AGENTS.md

backend-team-warehouse/      # Team-specific
├── knowledge/
│   └── languages/
│       └── python/**/*.md
└── contexts/
    └── teams/
        └── backend/

frontend-team-warehouse/     # Team-specific
├── knowledge/
│   └── languages/
│       └── typescript/**/*.md
└── contexts/
    └── teams/
        └── frontend/
```

**Project connects to multiple warehouses:**

Currently not supported - use one warehouse per project. Workaround: merge warehouses or use git submodules.

## Measuring Adoption

Track warehouse usage across team:

```bash
# In team-warehouse repo
git log --all --pretty=format:'%h %an %ad %s' --since="1 month ago"

# Count beacon.yaml references
grep -r "beacon.yaml" ../*/. --include="beacon.yaml" | wc -l
```

Create a dashboard:
- Projects using warehouse: X/Y
- Most-used artifacts: [list]
- Recent additions: [list]
- Pending PRs: [list]

## Best Practices

### 1. Clear Ownership

Assign maintainers to warehouse sections:
- `knowledge/languages/python/` → Python guild
- `knowledge/infrastructure/` → Platform team
- `contexts/teams/backend/` → Backend lead

### 2. Documentation

Every artifact should have:
- Clear purpose
- Usage examples
- Last updated date
- Owner/maintainer

### 3. Versioning Strategy

- Use semantic versioning for warehouse releases
- Tag stable versions: `v1.0.0`, `v1.1.0`
- Document breaking changes in CHANGELOG.md

### 4. Onboarding Process

Include in team onboarding:
1. Clone warehouse
2. Connect to warehouse in training project
3. Review team contexts
4. Complete "create your first beacon.yaml" exercise

### 5. Regular Maintenance

- **Monthly:** Review and prune outdated artifacts
- **Quarterly:** Major version releases with breaking changes
- **Ad-hoc:** Quick additions for new patterns

## Example: Complete Team Setup

**1. Create warehouse:**
```bash
abc warehouse init our-team-warehouse
cd our-team-warehouse
# ... populate with team content ...
git init && git add . && git commit -m "Initial commit"
git remote add origin git@github.com:ourteam/warehouse.git
git push -u origin main
```

**2. Team members connect:**
```bash
git clone git@github.com:ourteam/warehouse.git ~/our-team-warehouse
cd my-project
abc warehouse connect --path ~/our-team-warehouse
```

**3. Create beacon.yaml:**
```bash
abc setup
# Copy from example or create custom
abc sync
```

**4. Stay updated:**
```bash
# Pull warehouse changes
cd ~/our-team-warehouse && git pull

# Sync existing artifacts and discover new ones
cd my-project && abc sync

# If the sync output mentions new artifacts, adopt them interactively
abc adopt
```

## Troubleshooting

### Team member can't connect

**Check:** Warehouse location consistent
```bash
# Add to team README
echo "Clone warehouse to: ~/our-team-warehouse" >> README.md
```

### Artifacts out of sync

**Solution:** Have everyone pull and sync:
```bash
# Send to team chat
cd ~/our-team-warehouse && git pull && cd - && abc sync
```

### Conflicting patterns

**Problem:** Two projects use same pattern differently.

**Solution:** Create project-specific examples:
- `examples/beacon.yaml.api-service`
- `examples/beacon.yaml.background-worker`

## Next Steps

- **[Creating a Warehouse](./warehouse-creation.md)** - Detailed warehouse setup
- **[Advanced Patterns](./advanced-patterns.md)** - Complex configurations

---

**Related Guides:**
- [Getting Started](./getting-started.md)
- [Python Project Setup](./python-project-setup.md)
- [Warehouse Creation](./warehouse-creation.md)
