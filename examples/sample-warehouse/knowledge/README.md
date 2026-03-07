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
│   ├── typescript/
│   └── ...
└── domains/            # Domain-specific knowledge
    ├── data-platform/
    ├── web-services/
    └── ...
```

## Knowledge Types

### Decisions
Technical choices made and their rationale.

### Lessons
Patterns where agents commonly fail or get distracted.

### Facts
Established technical information and configurations.

## Selective Installation

When projects select contexts during setup, only relevant knowledge is copied:

```bash
abc setup --context python --knowledge global --knowledge languages/python
```

This copies only global and Python-specific knowledge to the project.
