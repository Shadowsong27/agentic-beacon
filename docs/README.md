# Documentation Overview

This directory contains **conceptual design documentation** that drives the agentic coding practices setup. For **practical how-to guides**, see the [guides/](../guides/) directory.

---

## Conceptual Design Documents

### Core Architecture

**[Agentic Warehouse Design](./agentic-warehouse-design.md)**
- High-level design philosophy and motivation
- Central repository model (contexts, knowledge, skills)
- Two-tier structure (context + knowledge)
- Component organization and discovery patterns
- Workflow: Setup → Use → Update → Contribute

### Boot Context Design

**[Boot Context Design](./boot-context-design/)**
- Comprehensive documentation on AGENTS.md architecture
- Three-tier context model (Warehouse → User → Project)

Files:
- **[agents-md-architecture.md](./boot-context-design/agents-md-architecture.md)** - Three-tier architecture overview, decision framework, anti-patterns
- **[project-level-agents-design.md](./boot-context-design/project-level-agents-design.md)** - Deep-dive into project-level AGENTS.md with detailed patterns

### Development Methodology

**[Spec-Driven Development](./spec-driven-development.md)**
- Structured approach to feature planning
- Two-phase process: Specification → Implementation
- Reduces ambiguity and improves AI collaboration

### Implementation Details

**[CLI Implementation Summary](./cli-implementation-summary.md)**
- Technical architecture of the warehouse CLI
- Package structure and key features
- Implementation decisions and testing approach

---

## Practical Guides

For step-by-step instructions and how-to guides, see:

- **[guides/cli-quick-start.md](../guides/cli-quick-start.md)** - Getting started with the CLI
- **[guides/warehouse-contribution-guide.md](../guides/warehouse-contribution-guide.md)** - Contributing improvements

---

## Document Purpose

| Document | Purpose | Audience |
|----------|---------|----------|
| `agentic-warehouse-design.md` | Understand the overall architecture | Architects, team leads setting up warehouse |
| `boot-context-design/agents-md-architecture.md` | Understand three-tier AGENTS.md model | Everyone writing AGENTS.md files |
| `boot-context-design/project-level-agents-design.md` | Learn how to write effective project AGENTS.md | Project maintainers |
| `spec-driven-development.md` | Learn structured feature planning | Developers planning features |
| `cli-implementation-summary.md` | Understand CLI architecture | CLI maintainers, contributors |

---

## Reading Order

**For new users:**
1. Start with [Agentic Warehouse Design](./agentic-warehouse-design.md) - understand the big picture
2. Read [agents-md-architecture.md](./boot-context-design/agents-md-architecture.md) - understand the three tiers
3. When creating project AGENTS.md, use [project-level-agents-design.md](./boot-context-design/project-level-agents-design.md) as reference
4. For practical usage, move to [guides/](../guides/)

**For contributors:**
1. Start with design docs to understand philosophy
2. Read [CLI Implementation Summary](./cli-implementation-summary.md) for technical details
3. Check [guides/warehouse-contribution-guide.md](../guides/warehouse-contribution-guide.md) for process

**For developers:**
1. Read [Spec-Driven Development](./spec-driven-development.md) first
2. Then [project-level-agents-design.md](./boot-context-design/project-level-agents-design.md) for context management
3. Use [guides/](../guides/) for day-to-day tasks
