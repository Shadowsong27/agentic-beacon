# Contexts Directory

This directory contains AGENTS.md context files organized by scope.

## Structure

```
contexts/
├── AGENTS.global.md           # Required for all projects (universal practices)
├── AGENTS.python.md           # Language-specific contexts
├── AGENTS.typescript.md
├── AGENTS.java.md
├── AGENTS.example-domain.md   # Domain-specific contexts (rename to your domain)
└── ...
```

## Types of Context Files

### Required Context
- **`AGENTS.global.md`** - Universal practices for all projects
  - Spec-driven development
  - Commit conventions
  - Session handoffs
  - Progressive disclosure patterns

### Optional Contexts

**Language-specific** (e.g., `AGENTS.python.md`)
- Standards for a specific programming language
- Type annotations, imports, testing patterns
- Select based on your project's primary language

**Domain-specific** (e.g., `AGENTS.data-platform.md`)
- Patterns for teams working in similar problem domains
- Infrastructure, tools, domain-specific practices
- Select based on your team or technical domain

## Creating New Context Files

1. **Determine scope**: Is this global, language, or domain-specific?
2. **Follow naming**: `AGENTS.<scope>.md` (e.g., `AGENTS.web-app.md`)
3. **Use progressive disclosure**: Brief summaries + pointers to knowledge files
4. **Reference knowledge**: Point to files in corresponding knowledge directory

## Usage

When projects run setup:
```bash
agentic-setup
? Select contexts:
  [x] Global (required)
  [x] Python
  [x] Data Platform
```

Selected context files are copied to `~/.agentic-context/` and loaded by agents via `opencode.json`.
