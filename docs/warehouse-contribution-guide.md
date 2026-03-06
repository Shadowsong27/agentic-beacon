# Warehouse Contribution Guide

Guide for contributing improvements to your organization's agentic engineering warehouse.

**Last Updated:** 2026-03-06

---

## Overview

This guide is for teams contributing to their **organization's warehouse instance** (created from this template), not the template repository itself.

---

## Contribution Workflow

### 1. Test Locally in Your Project

Before contributing back to the warehouse, validate changes in your project:

**For Context Files:**
```bash
# Edit context file in your project
vim ~/.agentic-context/AGENTS.python.md

# Test with agents in your project
# Verify agents follow the updated instructions correctly
```

**For Knowledge Files:**
```bash
# Edit knowledge file
vim ~/.agentic-context/knowledge/languages/python/lessons/new-lesson.md

# Reference from context and test
# Verify agents can access and use the knowledge
```

**For Skills:**
```bash
# Modify skill in your project
vim .opencode/skills/my-skill/SKILL.md

# Test the skill
/my-skill "test input"

# Verify it works as expected
```

---

### 2. Prepare Contribution

Once validated locally, prepare for warehouse contribution:

**Option A: Using CLI Tool (if available)**
```bash
# CLI prepares contribution
agentic-contribute --context AGENTS.python.md
agentic-contribute --knowledge python/lessons/new-lesson.md
agentic-contribute --skill my-skill
```

**Option B: Manual Preparation**
```bash
# Clone warehouse repository
git clone git@github.com:your-org/your-warehouse.git
cd your-warehouse

# Create feature branch
git checkout -b add-python-type-hints-lesson

# Copy files from your project
cp ~/.agentic-context/knowledge/languages/python/lessons/type-hints.md \
   knowledge/languages/python/lessons/

# Update context to reference new knowledge
vim contexts/AGENTS.python.md
```

---

### 3. Create Pull Request

**What to include in PR:**

1. **Clear title** following conventional commits:
   ```
   feat(python): add lesson on type hints best practices
   fix(context): correct typo in AGENTS.global.md
   docs(knowledge): improve PostgreSQL decision rationale
   ```

2. **Description with context:**
   ```markdown
   ## Summary
   Adds lesson on Python type hints based on recurring agent mistakes.

   ## Testing
   - Tested in project X for 2 weeks
   - Agents now correctly avoid quoted type annotations
   - No issues observed

   ## Impacted Files
   - contexts/AGENTS.python.md - added pointer
   - knowledge/languages/python/lessons/type-hints.md - new lesson

   ## Related Issues
   Closes #42
   ```

3. **Documentation updates:**
   - Update skills/README.md if adding new skill
   - Update knowledge/README.md if adding new knowledge structure
   - Add examples if introducing new patterns

---

### 4. Review Process

**For warehouse maintainers:**

1. **Validation checklist:**
   - [ ] Follows warehouse structure conventions
   - [ ] Knowledge files in correct scope (global/languages/domains)
   - [ ] Context references are correct paths
   - [ ] No project-specific details leaked into generic content
   - [ ] Examples are generic and reusable

2. **Quality checks:**
   - [ ] Markdown formatting correct
   - [ ] No broken links
   - [ ] Code examples tested
   - [ ] Follows progressive disclosure (context brief, knowledge detailed)

3. **Testing (if infrastructure exists):**
   - [ ] CI validates markdown syntax
   - [ ] CI checks for broken links
   - [ ] Skills tested against test projects

---

### 5. Merge and Distribution

Once approved and merged:

1. **Automatic distribution** (if CLI exists):
   - Teams run `agentic-update` to pull latest
   - CLI copies updated files to `~/.agentic-context/`

2. **Manual distribution** (if no CLI):
   - Teams pull warehouse repository
   - Copy updated files to their projects

3. **Communication:**
   - Announce significant changes to teams
   - Update CHANGELOG.md in warehouse
   - Tag releases for major updates

---

## Contribution Types

### Adding New Context

**When:** Your team uses a new language/domain not in warehouse

**Process:**
```bash
# 1. Create context file
vim contexts/AGENTS.go.md

# 2. Create corresponding knowledge directory
mkdir -p knowledge/languages/go/decisions
mkdir -p knowledge/languages/go/lessons

# 3. Add initial knowledge files
vim knowledge/languages/go/decisions/error-handling.md

# 4. Submit PR
git add contexts/AGENTS.go.md knowledge/languages/go/
git commit -m "feat(go): add Go language context and error handling guidance"
```

### Adding Knowledge to Existing Context

**When:** You discover a pattern/lesson worth sharing

**Process:**
```bash
# 1. Add knowledge file in correct scope
vim knowledge/languages/python/lessons/async-await-mistakes.md

# 2. Reference from context
vim contexts/AGENTS.python.md
# Add: **See:** [Async/await mistakes](...)

# 3. Submit PR
git commit -m "feat(python): add async/await common mistakes lesson"
```

### Adding New Skill

**When:** You create a reusable workflow

**Process:**
```bash
# 1. Create skill directory
mkdir -p skills/code-review

# 2. Add SKILL.md and supporting files
vim skills/code-review/SKILL.md
vim skills/code-review/templates/review-checklist.md

# 3. Update skills catalog
vim skills/README.md
# Add entry for code-review skill

# 4. Submit PR
git commit -m "feat(skills): add code review workflow skill"
```

### Updating Existing Content

**When:** Improving or correcting existing content

**Process:**
```bash
# 1. Make changes
vim knowledge/global/decisions/conventional-commits.md

# 2. Document what changed and why
git commit -m "docs(global): clarify conventional commits scope usage

- Add examples for optional scope
- Clarify when scope is recommended vs required
- Based on team feedback from 3 projects"
```

---

## Best Practices

### Keep It Generic

**❌ Bad (project-specific):**
```markdown
## Database Connection

Our production database is at db.acme.com:5432
Use the `ACME_DB_PASSWORD` environment variable
```

**✅ Good (generic and reusable):**
```markdown
## Database Connection

**Fact:** Database connection details should be in environment variables

**Pattern:**
- Host: `DATABASE_HOST`
- Port: `DATABASE_PORT`
- Password: `DATABASE_PASSWORD`
```

### Follow Pointer Conventions

**Proactive pointers** (`Read:`):
- Critical patterns affecting every file
- Common failure modes
- Standards requiring internalization

**Reactive pointers** (`See:`):
- Troubleshooting guides
- Detailed explanations
- Reference material for edge cases

### Test Thoroughly

Before contributing:
- [ ] Tested in at least one real project
- [ ] Verified agents use the content correctly
- [ ] Checked for no unintended side effects
- [ ] Validated all links and references work

### Document Context

In your PR description, explain:
- **Why** this is needed (problem it solves)
- **How** you tested it (which projects, duration)
- **Impact** on existing content (breaking changes?)

---

## Getting Help

**For questions about contributing:**
- Check warehouse documentation
- Ask in team chat/channel
- Contact warehouse maintainers

**For issues with the template structure:**
- See [Template Repository](https://github.com/Shadowsong27/agentic-engineering-warehouse-template)

---
