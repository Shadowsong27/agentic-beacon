# Knowledge Directory

Atomic, reusable knowledge organized by scope and type.

## Structure

```
knowledge/
├── global/              # Universal knowledge (all projects)
│   ├── decisions/
│   ├── lessons/
│   └── facts/
├── languages/          # Language-specific knowledge
│   ├── python/
│   │   ├── decisions/
│   │   └── lessons/
│   ├── typescript/
│   └── java/
└── domains/            # Domain-specific knowledge
    ├── data-platform/
    │   ├── decisions/
    │   ├── lessons/
    │   └── facts/
    └── web-app/
```

## Knowledge Types

### Decisions
Technical choices made and their rationale.

**Format:**
```markdown
## Decision: [Title]

**Context:** Why this decision was needed

**Options Considered:**
1. Option A - pros/cons
2. Option B - pros/cons

**Decision:** What we chose

**Rationale:** Why this is the best choice

**Consequences:** Trade-offs we accept
```

### Lessons
Patterns where agents commonly fail or get distracted.

**Format:**
```markdown
## Lesson: [Title]

**Agent Failure Mode:** How agents typically fail

**Correct Pattern:** What agents should do instead

**Guardrail:** Questions agents should ask before acting

**When this matters:** Context where this applies
```

### Facts
Established technical information and configurations.

**Format:**
```markdown
## Fact: [Title]

**Statement:** The fact itself

**Context:** When/where this applies

**Usage Notes:** How to use this information
```

## Organization by Scope

### Global (`knowledge/global/`)
- Universal knowledge for all projects
- Referenced by `AGENTS.global.md`
- Examples: Commit conventions, spec-driven development

### Languages (`knowledge/languages/`)
- Language-specific patterns and anti-patterns
- Referenced by language contexts (e.g., `AGENTS.python.md`)
- Examples: Type annotation rules, exception handling

### Domains (`knowledge/domains/`)
- Domain-specific infrastructure, tools, practices
- Referenced by domain contexts (e.g., `AGENTS.data-platform.md`)
- Examples: Infrastructure ports, workflow patterns

## Selective Installation

When projects select contexts during setup, only relevant knowledge is copied:

**Example:** Project selects Python + Data Platform
- Copies: `global/`, `languages/python/`, `domains/data-platform/`
- Skips: `languages/typescript/`, `domains/web-app/`

## Creating Knowledge Files

1. **Determine scope**: Global, language-specific, or domain-specific?
2. **Choose type**: Decision, lesson, or fact?
3. **Place correctly**: `knowledge/<scope>/<type>/<name>.md`
4. **Follow format**: Use appropriate template above
5. **Reference from context**: Add pointer in corresponding AGENTS.md file
