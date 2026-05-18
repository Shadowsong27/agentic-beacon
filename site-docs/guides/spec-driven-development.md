# Spec-Driven Development

A guide for using spec-driven development approaches in agentic engineering. The methodology is **orthogonal to Beacon proper** — Beacon distributes the artifacts that govern *how* an agent works, but a spec describes *what* it should build. Spec-driven workflows are a common way to author specs your agents can act on.

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

### Phase 1: Technical planning

**Goal:** Transform free-form ideas into a formal, implementation-ready technical plan.

**Process:**

1. **Listen and parse** — Extract core problem, goals, scope, technical ideas
2. **Generate first draft** — Create a structured technical planning document
3. **Audit and gap analysis** — Identify missing information, ask targeted questions
4. **Baseline** — Complete when all open questions are answered and the user approves

**Output — a technical planning document with:**

- Clear problem statement and goals
- Testable acceptance criteria
- Explicit in-scope and out-of-scope boundaries
- High-level technical approach
- Identified risks and dependencies
- Impacted modules/systems

### Phase 2: Task breakdown

**Goal:** Decompose the technical plan into granular, sequential implementation tasks.

**Process:**

1. **Source audit** — Access the planning document, scan the codebase for impacted modules
2. **Decomposition** — Break work into "sprints of one" atomic tasks
3. **Resolution** — Address ambiguities before starting implementation
4. **Handoff** — Deliver an actionable task checklist ready for execution

**Output — a task breakdown document with:**

- User story extracted from the plan
- Step-by-step implementation checklist
- Verification steps for each task
- Dependencies and execution order
- Manual intervention steps (if any)

---

## Packaging as Warehouse Skills

Spec-driven development workflows can be packaged as **skills** in your warehouse:

```
skills/
├── spec-propose/          # Phase 1: Create the technical plan
├── spec-breakdown/        # Phase 2: Create the task breakdown
└── spec-implement/        # Execute tasks from the breakdown
```

**Example usage:**

```bash
/spec-propose "Add user authentication with OAuth"
/spec-breakdown
/spec-implement
```

See [Creating Skills](creating-skills.md) for how to author and distribute the underlying `SKILL.md` files.

---

## Best Practices

### During planning

- **Be thorough** — better to over-specify than under-specify
- **Ask questions** — don't assume, clarify ambiguities
- **Think about failure** — what happens when things go wrong?
- **Identify manual steps early** — know what requires human intervention
- **Use diagrams** — Mermaid for complex flows

### During task breakdown

- **Small tasks** — each completable in one focused session
- **Verification steps** — every task needs a confirmation method
- **Logical order** — dependencies should flow naturally
- **Mark manual steps** — use `[MANUAL]` prefix to set expectations
- **Don't invent** — stick to what's in the technical plan

### General

- **Iterate** — specs improve with feedback
- **Version control** — commit after each phase
- **Link to knowledge** — store rationale and decisions in your warehouse
- **Keep readable** — write for humans first, AI second

---

## Document Templates

### Technical planning template

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

### Task breakdown template

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

## See Also

- [Specs vs. Artifacts](../concepts/specs-vs-artifacts.md) — why specs and warehouse artifacts live in different places
- [Creating Skills](creating-skills.md) — package spec workflows as distributable skills
