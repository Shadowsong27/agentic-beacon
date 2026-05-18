# Archive

Historical design and migration notes preserved for reference. These documents predate the current warehouse model and **should not be used as authoritative guidance** — the live documentation at <https://shadowsong27.github.io/agentic-beacon/> is the source of truth.

The archive is kept in-repo (rather than relying purely on git history) so that links and references in older commits, blog posts, and external write-ups continue to resolve.

---

## `boot-context-design/`

Original design notes for the three-tier `AGENTS.md` architecture (warehouse / user / project). The framing is partially reflected in today's [Philosophy](https://shadowsong27.github.io/agentic-beacon/concepts/philosophy/), [How It Works](https://shadowsong27.github.io/agentic-beacon/concepts/how-it-works/), and [Artifact Types](https://shadowsong27.github.io/agentic-beacon/concepts/artifact-types/) pages, but the operational detail is **opencode-centric and superseded** by the current artifact model (contexts + skills + knowledge + agents, each with its own wiring).

| File | Status |
|---|---|
| `agents-md-architecture.md` | Three-tier framing — partial concept retained in [Philosophy](https://shadowsong27.github.io/agentic-beacon/concepts/philosophy/) |
| `project-level-agents-design.md` | Predates current warehouse model. Treat as historical only. |
| `user-level-agents-design.md` | Minimal-by-design principle is still sound but Beacon does not actively manage user-level AGENTS.md today. |
| `naming-convention.md` | Superseded by `abc warehouse lint` rules and [Artifact Types](https://shadowsong27.github.io/agentic-beacon/concepts/artifact-types/). |

## `migrations/`

One-off migration records preserved verbatim. Each describes a since-completed structural change; the live behaviour is documented in the mkdocs site.

| File | Describes |
|---|---|
| `artifact-dependencies-frontmatter.md` | The introduction of `requires:` frontmatter on skills |
| `pending-artifacts-flow-and-record-revamp.md` | The introduction of `pending.yaml` and `.last-adopt`, and the revamped `record-knowledge` / `record-skill` flow |

For the current behaviour see [Pending & Adoption](https://shadowsong27.github.io/agentic-beacon/concepts/pending-and-adoption/) and [Artifact Types](https://shadowsong27.github.io/agentic-beacon/concepts/artifact-types/).
