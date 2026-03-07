# Global Context - PLACEHOLDER

**This is a template file. Replace with your organization's actual global context when forking.**

---

## What Goes Here

Universal practices and standards that apply to ALL projects in your organization:

- Commit conventions
- Code review requirements  
- Testing standards
- Security policies
- Documentation requirements
- Session handoff patterns
- Progressive disclosure guidelines

---

## Instructions for Customization

1. **Replace this file** with your organization's actual standards
2. **Keep it concise** - Use progressive disclosure (brief summary + link to detailed knowledge)
3. **Link to knowledge files** in `knowledge/global/` for details
4. **Update regularly** - Keep this file current as practices evolve

---

## Example Structure

```markdown
## Commit Conventions

**Brief:** Use Conventional Commits format for all commits.

**Format:** `<type>(<scope>): <description>`

**Read:** [Full guide](knowledge/global/decisions/conventional-commits.md)

---

## Code Review Process

**Brief:** All changes require PR review from at least one team member.

**Read:** [Review guidelines](knowledge/global/lessons/code-review-patterns.md)

---

## Testing Standards

**Brief:** Write tests for all new features and bug fixes.

**Read:** [Testing guide](knowledge/global/decisions/testing-strategy.md)
```

---

## Next Steps

1. Fork this template repository
2. Replace this placeholder with your organization's content
3. Add corresponding knowledge files in `knowledge/global/`
4. Distribute to your team using the CLI: `agentic setup --all`

---

**Last Updated:** [Your Date]
