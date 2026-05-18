# Philosophy

Three questions explain the choices behind Agentic Beacon — why the problem is worth solving at all, why the solution is plain markdown files instead of a retrieval system, and why the framework is intentionally lightweight.

---

## Why Do We Need This At All?

As teams adopt AI coding agents, inconsistent practices emerge quickly: each project develops its own conventions, agents receive different instructions, and valuable patterns discovered in one project never reach others. The result is fragmented quality, slow onboarding, and duplicated effort.

The answer is applying **DRY (Don't Repeat Yourself) to agentic knowledge**.

Instead of each project maintaining its own copy of coding standards, agent instructions, and learned patterns, centralize them in a warehouse where:

- **One update propagates everywhere** — fix a pattern once, all projects benefit
- **Teams learn collectively** — a lesson discovered in one project is shared with all
- **Onboarding is instant** — new developers and agents inherit organizational knowledge automatically
- **Nothing gets lost** — valuable conventions that emerge organically get captured and preserved

---

## Why Markdown Files Instead of a Local RAG System?

The short answer: **the problem doesn't need that solution.**

RAG (Retrieval-Augmented Generation) is designed for large-scale, unstructured, frequently-changing content where users don't know what they're looking for. A warehouse of organizational standards is none of those things.

| | File-based (Beacon's approach) | RAG-based |
|---|---|---|
| **Setup** | Clone a git repo | Vector DB + embedding pipeline + maintenance |
| **Dependencies** | Git, filesystem | Chroma/Pinecone/Weaviate, embedding models |
| **Adoption barrier** | Very low (everyone knows Git) | High (requires ML/infra expertise) |
| **Maintenance** | Standard Git workflow | DB maintenance, reindexing, embedding updates |
| **Versioning** | Native Git history | Custom versioning layer |
| **Human readability** | Direct markdown editing | Requires retrieval interface |
| **Contribution** | Standard PR workflow | More complex (embeddings must be regenerated) |

A warehouse stores curated, structured standards — typically hundreds of KB, not gigabytes. Agents don't need to *search* for relevant knowledge; context files tell them explicitly what to read and when. The two-tier pointer model (context → on-demand knowledge files) achieves the same goal as RAG without the infrastructure overhead.

RAG would make sense if the warehouse held thousands of unstructured documents, or if content changed hourly, or if users were doing exploratory search. None of those apply here.

---

## Why Keep This Lightweight?

**The agentic engineering landscape is shifting rapidly.** What's best practice today may be superseded in six months — by new agent capabilities, new tool conventions, new paradigms entirely. A heavy framework with strong opinions on structure bakes in assumptions that may not age well.

Keeping Agentic Beacon lightweight is a deliberate bet:

- **Low adoption cost** — teams can try it without committing to infrastructure
- **Easy to abandon or replace** — if something better comes along, migrating away is minimal (it's just markdown files and a small CLI)
- **Structure follows the team, not the tool** — the inner organization of your warehouse is yours to design; the framework only prescribes the four top-level directories and a minimum shape inside each
- **Works with any agent today** — no custom integrations, no proprietary formats; markdown files work with every coding agent that exists

The goal is to solve the DRY problem for agentic knowledge without creating a new dependency problem. A warehouse is just a Git repo. Artifacts are just markdown files. The CLI is just a sync tool. If the paradigm shifts again, your knowledge doesn't disappear — it's still plain text in a git repository.

---

## Two-Tier Information Model

A direct consequence of staying file-based is that agents need a way to scan boot context fast and pull deeper detail only when relevant. Beacon's structure formalises this as two tiers:

- **Tier 1 — Contexts** (boot context, loaded on session start): lightweight, scannable, contains summaries and pointers — *what does the agent need to know exists?*
- **Tier 2 — Knowledge** (deep context, loaded on demand): detailed explanations, rationale, examples — *what are the full details when needed?*

Pointers between the two come in two flavours:

- **Proactive pointers** (written as `**Read:**`) — agent must internalise immediately because the rule affects every file they touch.
- **Reactive pointers** (written as `**See:**`) — agent loads only when encountering the specific problem (troubleshooting, edge cases).

This separation is what keeps boot context cheap to load while preserving access to organisational depth. The taxonomy inside `knowledge/` — `decisions/`, `lessons/`, `facts/` — is enforced by `abc warehouse lint`; see [Artifact Types](artifact-types.md) for the operational rules.

---

## Next

- [How It Works](how-it-works.md) — the mechanics that follow from these choices
- [Artifact Types](artifact-types.md) — the four types and how each is wired
