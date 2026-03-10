# Decision: No Temporary Documentation in Repository

**Date:** 2026-03-07
**Status:** Active
**Context:** Agentic Beacon Framework

---

## Context

During agentic coding sessions, agents often create temporary handoff documentation to transfer context between sessions. These documents were accumulating in the repository (e.g., `PYPI_TOKEN_SETUP.md`, `RELEASE_AUTOMATION.md`, `SETUP.md` in `.github/workflows/`).

## Problem

Temporary handoff documents:
- Clutter the repository with outdated information
- Duplicate information that belongs in proper documentation
- Create confusion about what is official vs. temporary
- Are not maintained as permanent docs

## Decision

**Do NOT commit temporary handoff documentation created during agentic coding sessions.**

## Implementation

**Examples of temp docs that should NOT be committed:**
- Session handoff docs (e.g., `PYPI_TOKEN_SETUP.md`, `RELEASE_AUTOMATION.md`, `SETUP.md`)
- Implementation checklists created during development
- Agent-to-agent context transfer files
- One-off decision documents

**What to do instead:**
1. **Create them freely** during development for context continuity
2. **Use them** to transfer context between sessions
3. **Extract** any valuable information into proper documentation
4. **Delete them** before committing to the repository

**Proper documentation locations:**
- User-facing guides → `guides/`
- Design documentation → `docs/`
- Package-specific docs → `libs/beacon/` (e.g., README.md, QUICKSTART.md)
- Contribution guidelines → `CONTRIBUTING.md` (if needed)

## Consequences

**Positive:**
- Repository stays clean and focused
- Clear separation between temporary and permanent docs
- Proper documentation is kept up-to-date
- Less confusion for contributors

**Negative:**
- Requires discipline to delete temp docs before committing
- Useful information must be manually extracted to proper docs
- Slight overhead in cleanup process

## Alternatives Considered

1. **Keep all docs** - Rejected due to repository clutter
2. **Move to .temp/ folder** - Rejected as still commits temporary content
3. **Use .gitignore for temp docs** - Rejected as requires specific naming conventions
