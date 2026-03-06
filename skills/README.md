# Skills Catalog

Reusable workflows and procedures for agents.

**Last Updated:** 2026-03-06  
**Skills Count:** 1

---

## Available Skills

### example-skill
**Description:** A template skill showing the structure and format for creating new skills.

**Usage:** Reference this when creating new skills for your domain.

**Category:** Example/Template

---

## How to Use Skills

### Discovery
```bash
# List all skills
agentic-list skills

# Show skill details
agentic-show skill example-skill
```

### Installation
Skills are installed when you run project setup:
```bash
agentic-setup
? Select skills to install:
  [x] example-skill
```

### Invocation
Once installed, invoke skills using skill commands:
```bash
/example-skill "task description"
```

---

## Creating New Skills

1. **Create directory:** `skills/your-skill-name/`
2. **Add SKILL.md** with instructions for agents
3. **Optional:** Add `templates/`, `scripts/`, or `examples/` subdirectories
4. **Update this catalog** (agents maintain this file)
5. **Test locally** before contributing

See `example-skill/` for structure reference.

---

## Contributing Skills

1. Test skill in your project
2. Create pull request with skill directory
3. Update this catalog in your PR
4. Document what the skill does and when to use it
5. CI validates (if infrastructure exists)

---

_This file is maintained by agents when skills are added or updated._
