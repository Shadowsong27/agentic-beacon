# Global Context

Universal practices applicable to all projects using agentic coding.

**Last Updated:** 2026-03-06

---

## Spec-Driven Development

When implementing complex features, follow the two-phase approach:

**Phase 1: Technical Planning** - Create detailed spec with acceptance criteria  
**Phase 2: Task Breakdown** - Decompose into granular implementation tasks

**Read:** [Spec-driven development guide](~/.agentic-context/knowledge/global/decisions/spec-driven-development.md)

---

## Commit Conventions

Use Conventional Commits format for all commits.

**Format:** `<type>(<scope>): <description>`

**Common types:** feat, fix, refactor, docs, test, chore

**Read:** [Conventional commits guide](~/.agentic-context/knowledge/global/decisions/conventional-commits.md)

---

## Session Handoffs

When token consumption is high or context is too large for one session:

1. Create checkpoint with current state
2. Document what's complete and what's next
3. New session picks up from checkpoint

**See:** [Session handoff patterns](~/.agentic-context/knowledge/global/lessons/session-handoff-patterns.md)

---

## Progressive Disclosure

Keep context files minimal with pointers to detailed knowledge:

- **In context files:** 1-2 sentence summary + pointer
- **In knowledge files:** Full explanation with examples

**Example:**
```markdown
## Rule Name

**Rule:** Brief statement of the rule.

**Read:** [Detailed explanation](~/.agentic-context/knowledge/.../file.md)
```
