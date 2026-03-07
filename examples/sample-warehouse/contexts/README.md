# Contexts Directory

This directory contains AGENTS.md context files organized by scope.

## Structure

```
contexts/
├── AGENTS.global.md           # Required for all projects
├── AGENTS.<language>.md       # Language-specific contexts
└── AGENTS.<domain>.md         # Domain-specific contexts
```

## Creating New Context Files

1. **Determine scope**: Global, language, or domain-specific?
2. **Follow naming**: `AGENTS.<scope>.md` (e.g., `AGENTS.python.md`)
3. **Use progressive disclosure**: Brief summaries + pointers to knowledge files
4. **Reference knowledge**: Point to files in corresponding knowledge directory

## Usage

Teams select which contexts to install in their projects:

```bash
abc setup --context global --context python --context data-platform
```

Selected context files are copied to `.opencode/contexts/` in the project.
