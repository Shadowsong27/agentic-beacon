# Contributing to Starter Org Warehouse

## How to Contribute

### 1. Find Something to Add

- New coding standard → Add to contexts
- Technical decision → Document in knowledge/decisions
- Common mistake → Document in knowledge/lessons
- Reusable workflow → Create in skills

### 2. Follow Structure

**Contexts:** Brief summary + pointer to knowledge
**Knowledge:** Detailed explanation with examples
**Skills:** Step-by-step procedures

### 3. Test Locally

```bash
# Test distribution
cd ~/test-project
abc warehouse connect --path ~/path/to/this-warehouse
abc setup --manual
abc sync
abc status
```

### 4. Submit PR

- Clear title describing the change
- Link to related discussions or issues
- Explain why this addition is useful

## Guidelines

- **Be specific:** Vague guidance doesn't help agents
- **Be concise:** Agents have token limits
- **Include examples:** Show don't just tell
- **Keep updated:** Remove outdated information

## Questions?

Contact the platform team or open an issue.
