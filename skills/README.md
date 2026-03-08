# Skills Directory

This directory contains **reference copies** of project skills for documentation and version control purposes.

## Important: Skills Location

**These skills are NOT loaded by OpenCode from this location.**

For OpenCode to discover and load skills automatically, they must be placed in:
```
.agents/skills/<skill-name>/SKILL.md
```

## Workflow

1. **Development**: Edit skills in `.agents/skills/` - this is where OpenCode loads them from
2. **Maintenance**: Keep reference copies here in `skills/` for version control
3. **Updates**: When modifying a skill, update both locations:
   - Active version: `.agents/skills/<skill-name>/SKILL.md` (loaded by OpenCode)
   - Reference copy: `skills/<skill-name>/SKILL.md` (for documentation)

## Why Two Locations?

- **`.agents/skills/`** - OpenCode's discovery path (committed to git)
- **`skills/`** - Project documentation and reference (easier to browse)
- **`.opencode/skills/`** - Reserved for distributed/installed skills (gitignored)

## Available Skills

- `record-knowledge/` - Systematically capture decisions, lessons, and facts into the knowledge base

## Syncing Skills

To copy a skill from `.agents/skills/` to `skills/` after making changes:

```bash
cp .agents/skills/record-knowledge/SKILL.md skills/record-knowledge/SKILL.md
```

To update the active skill from the reference copy:

```bash
cp skills/record-knowledge/SKILL.md .agents/skills/record-knowledge/SKILL.md
```
