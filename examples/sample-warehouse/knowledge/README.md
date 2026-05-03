# Knowledge

This directory holds atomic knowledge units for your team.

## Structure

Organise however suits your team. A common starting point:

```
knowledge/
├── decisions/    # Technical choices and their rationale
├── lessons/      # Learnings from failures and successes
└── facts/        # Established configurations and references
```

## Example Entry

```markdown
---
type: decision
---

# Use Pydantic for Data Validation

We use Pydantic BaseModel for all data carriers.

**Why:** Strong typing, automatic validation, and great IDE support.
**Alternatives considered:** dataclasses (no validation), attrs (less ecosystem support).
```

Add entries here as your team accumulates knowledge. Reference them from context files using `**Read:** [link]` pointers.
