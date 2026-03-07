# Skills Directory

Reusable workflows and procedures for agents.

## Structure

```
skills/
└── skill-name/
    ├── SKILL.md           # Main skill instructions
    ├── templates/         # Optional: Template files
    ├── scripts/           # Optional: Helper scripts
    └── examples/          # Optional: Example usage
```

## Creating Skills

1. **Create directory:** `skills/your-skill-name/`
2. **Add SKILL.md** with instructions for agents
3. **Optional:** Add templates, scripts, or examples
4. **Test locally** before adding to warehouse

## Example Skill Structure

```markdown
# Skill: Deploy to Production

## Purpose
Guide agents through safe production deployment.

## When to Use
- Deploying new features to production
- Rolling back production deployments

## Procedure

1. **Verify tests pass**
   ```bash
   pytest tests/
   ```

2. **Create release tag**
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   ```

3. **Deploy**
   ```bash
   ./scripts/deploy.sh production
   ```

## Safety Checks
- [ ] All tests passing
- [ ] No breaking changes
- [ ] Changelog updated
```

## Installation

Teams install skills to their projects:

```bash
abc setup --skill deploy-production
```
