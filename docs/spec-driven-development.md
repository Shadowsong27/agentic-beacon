# Spec-Driven Development Guide

A guide for using spec-driven development approaches in agentic engineering.

**Last Updated:** 2026-03-06  
**Status:** Draft / To Be Expanded

---

## Overview

Spec-driven development is a methodology for transforming vague ideas into implementation-ready specifications through structured planning phases.

**When to use spec-driven development:**
- Complex, multi-component features
- Features requiring cross-team coordination
- Features with unclear or evolving requirements
- When you need to validate approach before significant implementation

**When NOT to use spec-driven development:**
- Simple, well-understood tasks (1-2 file changes)
- Bug fixes with clear root cause
- Routine maintenance tasks
- Prototyping or exploratory coding

---

## Two-Phase Approach

### Phase 1: Technical Planning

**Goal:** Transform free-form ideas into formal, implementation-ready technical plan

**Process:**
1. **Listen and Parse** - Extract core problem, goals, scope, technical ideas
2. **Generate First Draft** - Create structured technical planning document
3. **Audit and Gap Analysis** - Identify missing information, ask targeted questions
4. **Baseline** - Complete when all open questions answered and user approves

**Output:** Technical planning document with:
- Clear problem statement and goals
- Testable acceptance criteria
- Explicit in-scope and out-of-scope boundaries
- High-level technical approach
- Identified risks and dependencies
- Impacted modules/systems

### Phase 2: Task Breakdown

**Goal:** Decompose technical plan into granular, sequential implementation tasks

**Process:**
1. **Source Audit** - Access planning document, scan codebase for impacted modules
2. **Decomposition** - Break work into "sprints of one" atomic tasks
3. **Resolution** - Address ambiguities before starting implementation
4. **Handoff** - Deliver actionable task checklist ready for execution

**Output:** Task breakdown document with:
- User story extracted from plan
- Step-by-step implementation checklist
- Verification steps for each task
- Dependencies and execution order
- Manual intervention steps (if any)

---

## Integration with Agentic Warehouse

Spec-driven development workflows can be packaged as **skills** in your warehouse:

```
skills/
├── spec-propose/          # Phase 1: Create technical plan
├── spec-breakdown/        # Phase 2: Create task breakdown
└── spec-implement/        # Execute tasks from breakdown
```

**Example usage:**
```bash
# Phase 1: Create spec
/spec-propose "Add user authentication with OAuth"

# Phase 2: Break down into tasks
/spec-breakdown

# Execute implementation
/spec-implement
```

---

## Best Practices

### During Planning
- **Be thorough**: Better to over-specify than under-specify
- **Ask questions**: Don't assume—clarify ambiguities
- **Think about failure**: What happens when things go wrong?
- **Identify manual steps early**: Know what requires human intervention
- **Use diagrams**: Mermaid.js for complex flows

### During Task Breakdown
- **Small tasks**: Each completable in one focused session
- **Verification steps**: Every task needs confirmation method
- **Logical order**: Dependencies should flow naturally
- **Mark manual steps**: Use `[MANUAL]` prefix to set expectations
- **Don't invent**: Stick to what's in the technical plan

### General
- **Iterate**: Specs improve with feedback
- **Version control**: Commit after each phase
- **Link to knowledge**: Store decisions in warehouse
- **Keep readable**: Write for humans first, AI second

---

## Document Templates

### Technical Planning Template

```markdown
# [Feature Name]

## 1. Background and Problem Statement
[Clear synthesis of problem and why it needs solving]

## 2. Goals & Acceptance Criteria
- [ ] AC 1: [Testable criterion]
- [ ] AC 2: [Testable criterion]

## 3. Scope
### In Scope
[What will be implemented]

### Out of Scope
[What won't be implemented]

## 4. Proposed Technical Solution
### High-Level Architecture
[End-to-end flow and data lifecycle]

### Impacted Modules
- [Module/Path]: [Required modifications]

### Manual Intervention Requirements
- [Manual Step]: [Description and rationale]

## 5. Risks and Dependencies
- **Risk:** [Problem]
  - **Mitigation:** [Solution]

## 6. Open Questions
- [ ] [Question to resolve]
```

### Task Breakdown Template

```markdown
# Implementation Plan: [Feature Name]

## 1. User Story
[Extracted from technical plan]

## 2. Technical Summary
[Concise summary of solution]

## 3. Acceptance Criteria
- [ ] AC 1: [From technical plan]
- [ ] AC 2: [From technical plan]

## 4. Technical Task Checklist

### Phase 1: Preparation
- [ ] **Step 1:** [Action]
  - *Verification:* [How to check]

### Phase 2: Implementation
- [ ] **Step 2:** [Action]
  - *Verification:* [How to check]
- [ ] **[MANUAL] Step 3:** [User action required]
  - *User Action:* [What user needs to do]
  - *Verification:* [How to confirm]

## 5. Dependencies
[Internal/external dependencies]

## 6. Questions & Ambiguities
[Items needing resolution]
```

---

## Related Resources

- **[Agentic Warehouse Design](./agentic-warehouse-design.md)** - How to organize specs in your warehouse
- **Implementation Guide** - Building spec-driven skills _(coming soon)_

---

**Note:** This is a high-level overview. Detailed spec-driven development workflows will be added as skills to the warehouse as they evolve.
