# Global Engineering Standards

Universal practices that apply to all projects in this warehouse.

---

## Commit Conventions

**Brief:** Use Conventional Commits format for all commits.

**Format:** `<type>(<scope>): <description>`

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Examples:**
- `feat(auth): add OAuth2 login flow`
- `fix(api): handle null response from payment gateway`
- `docs: update getting started guide`

Breaking changes: append `!` after the type — `feat!: rename config to settings`

---

## Code Review

**Brief:** All changes require at least one peer review before merging.

- Keep PRs small and focused — one concern per PR
- Reviewers check correctness, readability, and test coverage
- Author resolves all comments before merging

---

## DRY Principle

**Brief:** Don't Repeat Yourself — every piece of knowledge should have a single source of truth.

- Extract shared logic into utilities rather than copy-pasting
- Prefer references and links over duplicating content
- If you find yourself writing the same thing twice, stop and abstract

---

## Testing

**Brief:** Write tests for all non-trivial logic. Tests live alongside the code they test.

- Unit tests for pure functions and business logic
- Integration tests for external boundaries (APIs, databases)
- Do not mock internal code — only mock at system boundaries

---

## Documentation

**Brief:** Document the *why*, not the *what*. Code explains what; comments and docs explain intent.

- Public APIs must have docstrings
- Complex logic requires an inline comment explaining the reasoning
- Keep docs current with code changes — stale docs are worse than no docs
