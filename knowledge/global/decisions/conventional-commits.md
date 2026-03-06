# Decision: Conventional Commits

**Context:** Teams need a consistent way to write commit messages for clear history and automated changelog generation.

**Options Considered:**

1. **Free-form commits** - No convention, developers write whatever they want
   - Pros: No learning curve, flexible
   - Cons: Inconsistent history, hard to parse, no automation

2. **Conventional Commits** - Structured format with types and scopes
   - Pros: Clear history, enables automation, widely adopted
   - Cons: Slight learning curve, requires discipline

3. **Custom format** - Organization-specific format
   - Pros: Tailored to needs
   - Cons: Not standard, harder for new developers

**Decision:** Use Conventional Commits format

**Rationale:**
- Industry standard with wide adoption
- Enables automated changelog generation
- Clear semantic meaning (feat vs fix vs chore)
- Works with semantic versioning tools
- Easy to learn and teach

**Format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Common Types:**
- `feat`: New feature or capability
- `fix`: Bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `docs`: Documentation changes only
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks, dependency updates
- `perf`: Performance improvements
- `ci`: CI/CD pipeline changes

**Examples:**
```bash
feat(auth): add OAuth2 authentication flow
fix(parser): handle empty input correctly
docs: update installation instructions
chore(deps): bump axios from 0.21.1 to 0.27.2
```

**Consequences:**
- Teams must learn the format (minimal investment)
- PR reviews should check commit message format
- CI can validate commit message format if desired

**References:**
- https://www.conventionalcommits.org/
