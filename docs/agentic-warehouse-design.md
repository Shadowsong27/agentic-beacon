# Agentic Warehouse Design

A high-level design guide for centralized context, knowledge, and skills management in agentic engineering.

**Last Updated:** 2026-03-06

> **Built for OpenCode:** This design was developed with [OpenCode](https://opencode.ai) usage in mind. While we keep patterns as generic as possible, the experience with other AI coding agents may differ. The core concepts (centralized context, progressive disclosure, DRY) remain applicable across tools.

---

## Table of Contents

1. [Why Centralized Management?](#why-centralized-management)
2. [Central Repository Model](#central-repository-model)
   - [Understanding the Two-Tier Structure: Context + Knowledge](#understanding-the-two-tier-structure-context--knowledge)
3. [Component 1: Contexts (AGENTS.md Organization)](#component-1-contexts-agentsmd-organization)
   - [What Are Contexts?](#what-are-contexts)
   - [Multi-Tier Context Model](#multi-tier-context-model)
   - [Progressive Disclosure Pattern](#progressive-disclosure-pattern)
   - [What Goes Where?](#what-goes-where)
   - [Collaboration Benefits](#collaboration-benefits)
4. [Component 2: Stateless Knowledge](#component-2-stateless-knowledge)
   - [What is Stateless Knowledge?](#what-is-stateless-knowledge)
   - [Organization Structure](#organization-structure)
   - [Discovery: Proactive vs Reactive Pointers](#discovery-proactive-vs-reactive-pointers)
   - [Example: Lesson File Structure](#example-lesson-file-structure)
   - [Storage Strategy](#storage-strategy)
5. [Component 3: Skills Organization](#component-3-skills-organization)
   - [What Are Skills?](#what-are-skills)
   - [Skills vs Knowledge](#skills-vs-knowledge)
   - [Organization Structure](#organization-structure-1)
   - [Discovery](#discovery)
   - [Skill Invocation](#skill-invocation)
   - [Testing and Contribution](#testing-and-contribution)
6. [Workflow: Setup → Use → Update → Contribute](#workflow-setup--use--update--contribute)
   - [1. Setup (One-time per project)](#1-setup-one-time-per-project)
   - [2. Use (Daily development)](#2-use-daily-development)
   - [3. Update (Periodic sync)](#3-update-periodic-sync)
   - [4. Contribute (Give back improvements)](#4-contribute-give-back-improvements)
   - [Technical Notes](#technical-notes)

---

## Why Centralized Management?

**The agentic engineering landscape is rapidly evolving.** Vibe coding practices, AI agent capabilities, and collaboration paradigms shift weekly. In this fluid environment, rigid methodologies quickly become outdated. Instead of prescribing how teams should work with AI agents, this guide provides a **minimal, flexible structure** for centralizing reusable knowledge.

**The problem without centralization:**

As teams adopt AI coding agents, inconsistent practices emerge: each project develops its own conventions, agents receive different instructions, and valuable patterns remain siloed. This fragmentation slows onboarding, creates quality variations, and wastes collective learning.

**The solution: Apply DRY (Don't Repeat Yourself) to agentic knowledge.**

Rather than duplicating agent instructions, coding standards, and learned patterns across projects, centralize them in a warehouse where:
- **One update propagates everywhere** - Fix a pattern once, all projects benefit
- **Teams learn collectively** - Capture lessons from one project, share with all
- **Onboarding is instant** - New developers and agents inherit organizational knowledge automatically
- **Evolution is natural** - Adapt as practices shift without rewriting every project

This approach establishes **standardized collaboration patterns** while remaining flexible enough to evolve with the rapidly changing agentic engineering landscape.

### Why Simple File-Based Distribution Over RAG?

**Design decision: Keep it simple.** This warehouse uses plain files and Git instead of RAG (Retrieval-Augmented Generation) systems. Here's why:

**The use case doesn't require RAG complexity:**

Agentic coding operates in a fundamentally different context than production systems:
- **Speed requirements:** Agents already spend seconds reading code and searching files. Adding milliseconds for file reads is negligible. We don't need microsecond vector search.
- **Content scale:** Warehouse stores curated organizational standards (~100s of KB), not massive documentation (GBs). RAG is designed for scale we don't have.
- **Access patterns:** Explicit pointers (e.g., "Read: knowledge/python/lessons/type-annotations.md") work better than semantic search for structured standards.
- **Update frequency:** Standards evolve slowly (weeks/months), not constantly. No need for continuous reindexing.

**Simple file-based approach advantages:**

| Aspect | File-Based (Our Choice) | RAG-Based |
|--------|------------------------|-----------|
| **Setup** | Copy markdown files | Vector DB + embedding pipeline + maintenance |
| **Dependencies** | Git, filesystem | Chroma/Pinecone/Weaviate, embedding models, vector DB |
| **Adoption barrier** | Very low (everyone knows Git) | High (requires ML/infrastructure expertise) |
| **Maintenance** | Standard Git workflow | DB maintenance, reindexing, embedding updates |
| **Speed** | 1-5ms file reads | Sub-millisecond vector search (unnecessary here) |
| **Versioning** | Native Git history | Custom versioning layer |
| **Human readability** | Direct markdown editing | Requires retrieval interface |
| **Contribution** | Standard PR workflow | More complex (embeddings must be regenerated) |

**Progressive disclosure without RAG:**

Our two-tier model provides memory management naturally:
- **Tier 1 (Boot context):** AGENTS.md files load immediately - kept minimal, scanned quickly
- **Tier 2 (Knowledge files):** Accessed on-demand via explicit pointers - agents know exactly where to look

This achieves the same goal as RAG (avoiding context overload) with simpler mechanisms.

**When you WOULD need RAG:**
- Semantic search across thousands of unstructured documents
- Finding similar code patterns across millions of lines
- Content that changes constantly (hourly/daily)
- Users who don't know what they're looking for (exploratory search)

**Why warehouse doesn't need RAG:**
- Content is curated and structured (not unstructured documents)
- Small scale (organizational standards, not documentation websites)
- Explicit discovery (pointers tell agents exactly where to look)
- Infrequent updates (standards evolve deliberately)
- Human review is critical (markdown files are easier to review than embeddings)

**Bottom line:** RAG adds complexity without proportional benefit for this use case. Simple, git-based file distribution is faster to adopt, easier to maintain, and sufficient for organizational knowledge management in agentic coding.

---

## Central Repository Model

All reusable context, knowledge, and skills live in a **central repository** with this structure:

```
agentic-engineering-central/
├── contexts/         # AGENTS.md files (global, language, domain)
├── knowledge/        # Decisions, lessons, facts (referenced by contexts)
└── skills/           # Reusable workflows and procedures
```

**Key principles:**
- **Single source of truth:** Updates propagate to all projects
- **Versioned:** Changes go through PR review
- **Discoverable:** CLI provides interactive selection
- **Testable:** Skills include test harnesses for validation

The repository acts as a "warehouse" where projects select what they need, install locally, and stay synchronized with organizational standards.

### Understanding the Two-Tier Structure: Context + Knowledge

This design uses a **two-tier approach** to manage agent information efficiently:

**Tier 1: Contexts** (Boot context - loaded immediately)
- Lightweight context files that agents see on session start
- Contains **summaries and pointers**, not full details
- Think: "What does the agent need to know exists?"
- Kept minimal to reduce token consumption

**Naming conventions:**
- **Warehouse level:** Simple filenames (e.g., `global.md`, `python.md`, `data-platform.md`)
- **Project level:** Single `AGENTS.md` file (at `<project>/.opencode/AGENTS.md`)
- **User level:** Single `AGENTS.md` file (at `~/.config/opencode/AGENTS.md`)

The warehouse uses flexible naming because files are loaded via `opencode.json` configuration. Project and user levels use `AGENTS.md` as a convention for easy identification.

**Tier 2: Knowledge** (Deep context - loaded on demand)
- Detailed explanations, rationale, examples
- Referenced by contexts via pointer system
- Think: "What are the full details when needed?"
- Agents pull this when they need deeper understanding

**Why both?**

Without this separation, AGENTS.md files become bloated with details agents rarely need, wasting tokens and making it hard to scan. The two-tier approach enables:
- **Fast scanning:** Agents quickly find relevant topics in contexts
- **Progressive disclosure:** Agents dive deep only when needed
- **Token efficiency:** Don't load detailed rationale for every rule on every session
- **Maintainability:** Update detailed docs without cluttering boot context

**Examples:**

**Example 1: Proactive Pointer (Agent must read immediately)**

```markdown
# In python.md (Tier 1: Context)
## Type Annotations

**Rule:** Only quote type annotations for forward references.

**Read:** [Common mistakes](~/.agentic-context/knowledge/languages/python/lessons/quoted-type-annotations.md)
```

```markdown
# In knowledge/languages/python/lessons/quoted-type-annotations.md (Tier 2: Knowledge)
## Lesson: Agents Often Over-Quote Type Annotations

**Agent Failure Mode:** Agents quote all type annotations unnecessarily:

# Incorrect - unnecessary quotes
def process(data: "list[Document]") -> "ProcessedResult":
    return result

**Correct Pattern:** Only quote for forward references or circular imports:

# Correct - no quotes for available types
def process(data: list[Document]) -> ProcessedResult:
    return result

**Guardrail:** Before quoting a type annotation, ask:
1. Is this a forward reference (type defined later in file)?
2. Is this avoiding a circular import?
3. If neither, remove the quotes.
```

**Example 2: Reactive Pointer (Agent reads when needed)**

```markdown
# In data-platform.md (Tier 1: Context)
## Troubleshooting

If DAG parsing fails, consult the debugging checklist.

**See:** [Airflow debugging checklist](~/.agentic-context/knowledge/domains/data-platform/lessons/airflow-debugging-checklist.md)
```

```markdown
# In knowledge/domains/data-platform/lessons/airflow-debugging-checklist.md (Tier 2: Knowledge)
## Lesson: Pre-Flight Checklist for Airflow Debugging

Run this checklist BEFORE debugging anything. 60% of issues are caught here.

**Step 1: Environment Variables**
```bash
echo $DOT_PROJECT_PATH  # Should be set
echo $AIRFLOW_HOME      # Should be set
```

**Step 2: Services Running**
```bash
docker ps | grep airflow  # Should show containers
```

**Step 3: Config Loaded**
```bash
psql $DATABASE_URL -c \
  "SELECT COUNT(*) FROM pipeline_configs WHERE workspace='your_workspace';"
# Should return > 0
```

[... detailed troubleshooting steps continue ...]

**Key difference:**
- **Proactive (`Read:`)**: Agent must load immediately—affects every file they touch
- **Reactive (`See:`)**: Agent loads only when encountering the specific problem

---

## Component 1: Contexts (Boot Context Organization)

### What Are Contexts?

Context files serve as **boot context** - the knowledge agents see immediately on session start. They provide instructions, standards, and pointers to deeper knowledge.

**Naming conventions:**
- **Warehouse:** Simple filenames like `global.md`, `python.md`, `data-platform.md`
- **Project:** Single `AGENTS.md` at `<project>/.opencode/AGENTS.md`
- **User:** Single `AGENTS.md` at `~/.config/opencode/AGENTS.md`

### Multi-Tier Context Model

Context is organized into three tiers:

**Required Context: Global**
- Universal practices applicable to all projects
- **Examples:** Spec-driven development, session handoff patterns, commit conventions
- **When to use:** Always included in every project setup

**Optional Contexts: Modular**
- **Language-specific:** Python, TypeScript, Java, Go, etc.
  - Standards for a specific programming language
  - Examples: Python type annotation rules, TypeScript interface patterns
- **Domain-specific:** Data Platform, Web App, ML/AI, DevOps, etc.
  - Patterns for teams working in similar problem domains
  - Examples: Data Platform (PostgreSQL, Airflow, DBT), Web App (Auth, API design)
- **Mix and match:** Choose multiple contexts based on project needs
- **When to use:** Select what applies to your project's technology stack and problem domain

**Project Context: Unique**
- Project-specific architecture, troubleshooting guides, module references
- **Examples:** "Our microservices communicate via gRPC", "See docs/architecture.md for service map"
- **When to use:** Information that only applies to this specific codebase

### Progressive Disclosure Pattern

Context files should be a **pointer system**, not an encyclopedia. 

**In context files:**
- 1-2 sentence summary of the pattern or rule
- Reference to detailed knowledge elsewhere

**Example:**
```markdown
## Database Standards

**Rule:** Always use PostgreSQL for development, never SQLite.

**Rationale:** [See decision doc](~/.agentic-context/knowledge/decisions/postgres-over-sqlite.md)

**Troubleshooting:** [Connection pool guide](~/.agentic-context/knowledge/lessons/postgres-troubleshooting.md)
```

**Benefits:**
- Keeps context files scannable (agents can quickly find what they need)
- Detailed knowledge lives in searchable, versioned files
- Agents pull deeper context only when needed

### What Goes Where?

**Decision framework:**

| Question | Yes → | No → |
|----------|-------|------|
| Does this apply to all projects org-wide? | **Global context** (`global.md`) | ↓ |
| Does this apply to all projects using this language? | **Language context** (e.g., `python.md`) | ↓ |
| Does this apply to multiple teams in the same domain? | **Domain context** (e.g., `data-platform.md`) | ↓ |
| Is this unique to this project? | **Project AGENTS.md** | ↓ |
| Is this a detailed explanation? | **Knowledge file** (reference from context) | |

**Anti-patterns to avoid:**
- ❌ Copying the same pattern into multiple project `AGENTS.md` files → Promote to warehouse context
- ❌ Putting implementation details in context files → Extract to knowledge file
- ❌ Creating language-specific patterns used by only one team → Consider if it's truly language-wide or just domain-specific

### Collaboration Benefits

**For teams:**
- **Consistency:** All projects using the same language/stack see the same standards
- **Evolution:** Improvements in one project benefit all others
- **Onboarding:** New developers get full context automatically
- **Discoverability:** CLI shows what's available, teams don't need to guess

**For individuals:**
- **Minimal setup:** Install once, works everywhere
- **Stay current:** Update command pulls latest standards
- **Contribute easily:** Proven patterns flow back to central repo
- **Override when needed:** Project `AGENTS.md` can override warehouse contexts for special cases

---

## Component 2: Stateless Knowledge

### What is Stateless Knowledge?

Stateless knowledge represents **timeless, atomic, reusable insights** - decisions made, lessons learned, and established facts that remain valid across projects and sessions. Unlike session-specific context or runtime state, this knowledge is **stable, shareable, and reference-able**.

**Three types of stateless knowledge:**

**Decisions**
- Technical choices made and their rationale
- Examples: "Why Pydantic over dataclasses", "Why PostgreSQL over SQLite"
- Format: Problem → Options → Decision → Rationale

**Lessons**
- Patterns where agents commonly fail or get distracted
- Anti-patterns and guardrails to prevent repeated mistakes
- Examples: "Agents over-quote type annotations", "Agents create premature abstractions"
- Format: Agent failure mode → Correct pattern → Guardrail

**Facts**
- Established technical information and configurations
- Examples: "Database port mappings", "API endpoint patterns", "Naming conventions"
- Format: Statement → Context → Usage notes

### Organization Structure

Knowledge is organized to **mirror context structure**, enabling selective import based on which contexts a project uses.

```
knowledge/
├── global/                          # Universal knowledge (all projects)
│   ├── decisions/
│   │   └── conventional-commits.md
│   ├── lessons/
│   │   └── session-handoff-patterns.md
│   └── facts/
│       └── git-workflow.md
├── languages/                       # Language-specific knowledge
│   ├── python/
│   │   ├── decisions/
│   │   │   └── why-pydantic-over-dataclass.md
│   │   └── lessons/
│   │       └── quoted-type-annotations.md
│   ├── typescript/
│   │   ├── decisions/
│   │   └── lessons/
│   └── java/
│       └── decisions/
└── domains/                         # Domain-specific knowledge
    ├── data-platform/
    │   ├── decisions/
    │   │   └── two-workflow-approach.md
    │   ├── lessons/
    │   │   └── airflow-debugging-checklist.md
    │   └── facts/
    │       └── infrastructure-ports.md
    ├── web-app/
    │   ├── decisions/
    │   │   └── auth-pattern.md
    │   └── facts/
    │       └── api-endpoints.md
    └── ml-ai/
        ├── decisions/
        └── lessons/
```

**Knowledge organization by scope:**

**Global knowledge** (`knowledge/global/`)
- Referenced by `global.md` (required for all projects)
- Universal practices: commit conventions, session handoffs, spec-driven development

**Language knowledge** (`knowledge/languages/*/`)
- Referenced by language-specific contexts (e.g., `python.md`, `typescript.md`)
- Language-specific patterns and anti-patterns

**Domain knowledge** (`knowledge/domains/*/`)
- Referenced by domain-specific contexts (e.g., `data-platform.md`, `web-app.md`)
- Domain-specific infrastructure, tools, and practices

**Selective installation:** When teams run setup and select contexts, the CLI only copies relevant knowledge directories to `~/.agentic-context/`. A project using Python + Data Platform gets `global/`, `languages/python/`, and `domains/data-platform/` knowledge, but not `web-app/` or `typescript/` knowledge.

### Discovery: Proactive vs Reactive Pointers

Agents discover knowledge through **pointer systems** in context files with two modes:

**Proactive Pointers (Agent must read immediately)**

Example in `global.md`:
```markdown
## Commit Conventions

**Rule:** Use conventional commits format for all commits.

**Read:** [Conventional commits guide](~/.agentic-context/knowledge/global/decisions/conventional-commits.md)
```

Example in `data-platform.md`:
```markdown
## Development Workflow

**Rule:** Use two-workflow approach (venv for parsing, Docker for execution).

**Read:** [Two-workflow decision](~/.agentic-context/knowledge/domains/data-platform/decisions/two-workflow-approach.md)
```

Use proactive pointers for:
- Critical patterns agents must internalize before coding
- Common failure modes agents encounter frequently
- Standards that affect every file they touch

**Reactive Pointers (Agent reads when needed)**

Example in `data-platform.md`:
```markdown
## Troubleshooting

If DAG parsing fails, consult the debugging checklist.

**See:** [Airflow debugging checklist](~/.agentic-context/knowledge/domains/data-platform/lessons/airflow-debugging-checklist.md)
```

Use reactive pointers for:
- Troubleshooting guides consulted during errors
- Detailed explanations of complex topics
- Reference material for edge cases

### Example: Lesson File Structure

**File:** `knowledge/languages/python/lessons/quoted-type-annotations.md`

**Content:**
```
## Lesson: Agents Often Over-Quote Type Annotations

**Agent Failure Mode:** Agents quote all type annotations unnecessarily:

# Incorrect - unnecessary quotes
def process(data: "list[Document]") -> "ProcessedResult":
    return result

**Correct Pattern:** Only quote for forward references or circular imports:

# Correct - no quotes for available types
def process(data: list[Document]) -> ProcessedResult:
    return result

# Correct - quotes only for forward reference
def create_node(self) -> "TreeNode":
    return TreeNode()

**Guardrail:** Before quoting a type annotation, ask:
1. Is this a forward reference (type defined later in file)?
2. Is this avoiding a circular import?
3. If neither, remove the quotes.

**When this matters:** Python 3.10+ with `from __future__ import annotations` makes quotes unnecessary in most cases.
```

### Storage Strategy

**Minimize AGENTS.md, maximize knowledge files:**

**In context file (minimal):**
```markdown
## Type Annotations

Use primitive types when available (`list` not `List`).

**Read:** [Common annotation mistakes](~/.agentic-context/knowledge/languages/python/lessons/quoted-type-annotations.md)
```

**In knowledge file (detailed):**
- Full context and examples
- Agent failure modes
- Correct patterns with code samples
- Guardrails and decision criteria

**Benefits:**
- Context files stay scannable
- Knowledge is searchable and versioned
- Multiple contexts can reference the same knowledge
- Teams can update knowledge without touching all contexts

---

## Component 3: Skills Organization

### What Are Skills?

Skills are **reusable workflows, procedures, and specialized contexts** that agents can load on-demand. Unlike knowledge (which is atomic and informational), skills are **procedural and actionable**.

**Skills encompass everything that is not knowledge:**

**Procedural Workflows**
- Multi-step processes agents follow
- Examples: "Create a new spec", "Review pull request", "Debug Airflow DAGs"

**Context Injections**
- Specialized instructions loaded for specific tasks
- Examples: "Load DBT development patterns", "Activate security review mode"

**Templates and Patterns**
- Structured documents or code patterns
- Examples: "API endpoint template", "Test file structure"

**Executable Procedures**
- Scripts, tools, or automation bundled with instructions
- Examples: "Setup script + usage guide", "Diagnostic tool + interpretation guide"

### Skills vs Knowledge

| Aspect | Knowledge | Skills |
|--------|-----------|--------|
| **Nature** | Informational, atomic | Procedural, multi-step |
| **Scope** | Reusable facts/decisions/lessons | Complete workflows |
| **Level** | Global or optional contexts only | Can be project-specific |
| **Format** | Short markdown files | Instructions + optional templates/scripts |
| **Usage** | Referenced via pointers | Invoked via skill commands |

**Example distinction:**
- **Knowledge:** "Lesson: Agents over-quote type annotations" (what mistake to avoid)
- **Skill:** "Python type checking workflow" (how to systematically check types in a codebase)

### Organization Structure

Skills use a **flat structure** in the central repository:

```
skills/
├── README.md                      # Catalog (agent-maintained)
├── openspec-propose/
│   ├── SKILL.md                   # Primary instructions
│   └── templates/                 # Optional templates
│       └── task_brief.md.template
├── openspec-apply-change/
│   └── SKILL.md
├── pr-review/
│   ├── SKILL.md
│   └── checklists/                # Optional supporting files
│       └── security-checklist.md
└── airflow-debug/
    ├── SKILL.md
    └── scripts/                   # Optional diagnostic scripts
        └── check-config.sh
```

**Naming convention:** Use kebab-case for skill directories (e.g., `openspec-propose`, not `openspec_propose`)

**Optional components within a skill:**
- `templates/` - Structured documents agents fill out
- `scripts/` - Helper scripts or diagnostic tools
- `checklists/` - Reference checklists for complex workflows
- `examples/` - Sample outputs or usage examples

### Discovery

**Primary method: CLI**
```bash
# List all available skills
$ agentic-list skills

Available skills:
  - openspec-propose: Create new OpenSpec change with design and tasks
  - openspec-apply-change: Implement tasks from an OpenSpec change
  - pr-review: Comprehensive code review for pull requests
  - airflow-debug: Debug Airflow DAG parsing and execution issues

# Show skill details
$ agentic-show skill openspec-propose
```

**Secondary method: Browse repository**
- Navigate to `skills/README.md` in the central repository
- Catalog is maintained by agents when skills are added or updated
- Includes skill name, description, and usage notes

### Skill Invocation

Once installed in a project, agents invoke skills using skill commands:

```bash
# Example invocations
/openspec-propose "Add user authentication"
/pr-review
/airflow-debug --check-parsing
```

The skill's `SKILL.md` contains detailed instructions agents follow when invoked.

### Testing and Contribution

**Testing:** Validation strategies for skills are project-specific. Common approaches include:
- Manual validation in test projects
- Automated test harnesses (if skill includes scripts)
- Peer review before merging to central repo

**Contribution:** Workflows for contributing improved skills back to the central repository are covered in separate operational documentation.

**Note:** Both testing and contribution processes depend on organizational practices and tooling. Teams should establish their own conventions based on their CI/CD infrastructure and review processes.

---

## Workflow: Setup → Use → Update → Contribute

### 1. Setup (One-time per project)

Run CLI tool with interactive selection:
- Choose language contexts (Python, TypeScript, etc.)
- Choose domain contexts (Data Platform, Web App, etc.)
- Choose skills to install

**Result:**
- Context files copied to standard location (`~/.agentic-context/`)
- Skills copied to project (`.opencode/skills/`)
- Project's `opencode.json` configured to reference all contexts
- Project's `AGENTS.md` created for project-specific content

### 2. Use (Daily development)

Agents automatically load all configured contexts on session start. Developers don't think about it - it just works.

### 3. Update (Periodic sync)

Run sync command to pull latest from central repo:
- Context files updated in standard location
- Skills updated in project
- Version conflicts flagged for manual review

### 4. Contribute (Give back improvements)

When you improve a skill or discover a pattern worth sharing:
- Test locally in your project
- Use contribution command to prepare for central repo
- Submit PR with test results
- CI validates against test projects
- Once merged, available to all teams

### Technical Notes

- **Standard location:** Context files live in `~/.agentic-context/` to avoid path differences across machines
- **OpenCode native support:** The `instructions` field in `opencode.json` loads multiple files automatically
- **Glob patterns supported:** Can reference `docs/**/*.md` for dynamic inclusion
- **Load order matters:** Project AGENTS.md loads last, so it can override global patterns

---
