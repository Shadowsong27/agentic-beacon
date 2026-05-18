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

A direct consequence of staying file-based is that the warehouse needs to be cheap to load at session start without sacrificing organisational depth. Beacon's structure addresses this with two related artifact types, and an optimisation pattern that connects them:

- **Contexts** are the boot-time payload — the agent loads them on session start. A context is, in effect, a curated collection of knowledge: it can hold short rules and patterns inline AND point at deeper material elsewhere.
- **Knowledge files** are atomic units — one decision, one lesson, one fact, in its own file. They can be referenced from one or more contexts (or from other knowledge files), and they exist as standalone files so the same knowledge can be composed into multiple contexts and so it can be left out of the boot-time payload when it's not needed every session.

Within a context, two link styles signal how the linked content should be treated:

- **Proactive pointers** (`**Read:**`) — the linked content matters often enough that the agent should load it immediately when starting work in this area.
- **Reactive pointers** (`**See:**`) — the linked content is troubleshooting, edge-case detail, or reference material; the agent only loads it when the specific situation arises.

The progressive-disclosure pattern that emerges from these pointer styles is an **optimisation**, not the definition of either artifact. Not all knowledge is hidden at session start; some of it lives inline in a context because the rule applies every session and is short enough that hiding it would just force an extra link-follow. The extraction decision — *should this be inline content in the context, or its own knowledge file?* — is a judgement call, covered in the [Creating Knowledge and Contexts](../guides/creating-knowledge-and-contexts.md) guide.

The taxonomy inside `knowledge/` — `decisions/`, `lessons/`, `facts/` — is enforced by `abc warehouse lint`; see [Artifact Types](../concepts/artifact-types.md) for the operational rules.

---

## Next

- [How It Works](../concepts/how-it-works.md) — the mechanics that follow from these choices
- [Artifact Types](../concepts/artifact-types.md) — the four types and how each is wired
