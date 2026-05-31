# Canonical Links

Warehouse artifacts use one canonical link form for any reference that points at
another artifact in the same warehouse:

```text
.agentic-beacon/artifacts/<warehouse-relative-path>
```

Example:

```markdown
[Team context](.agentic-beacon/artifacts/contexts/team-context.md)
[Python standards](.agentic-beacon/artifacts/knowledge/python/standards.md#section-a)
[Deep review checklist](.agentic-beacon/artifacts/agent-partials/deep-review-checklist.md)
```

The last example matters because agents are distributed outside the artifact mirror
into `.claude/agents/` and `.opencode/agents/`. Canonical form is the only link style
that still resolves for an agent pointing at a shared partial.

---

## Resolution Rule

Beacon resolves a canonical link by stripping the `.agentic-beacon/artifacts/` prefix
and treating the rest as a path relative to the warehouse root.

- `.agentic-beacon/artifacts/contexts/team-context.md`
  resolves to `contexts/team-context.md` in the warehouse.
- `.agentic-beacon/artifacts/knowledge/python/standards.md#section-a`
  resolves to `knowledge/python/standards.md`, then validates `section-a` against
  the target file's headings using GitHub-compatible slugification.

In a synced project this is equivalent to checking that
`<project-root>/.agentic-beacon/artifacts/<warehouse-relative-path>` exists.

---

## Link Categories

Beacon classifies every inline markdown link into one of four meaningful categories
plus absolute URLs:

| Category | Meaning | Outcome |
|---|---|---|
| Absolute URL | External target such as `https://...` or `mailto:...` | Allowed; ignored by canonical-link lint |
| Canonical | Begins with `.agentic-beacon/artifacts/` | Allowed if the target file and optional anchor resolve |
| Own-folder relative | Relative link that stays inside the current skill directory | Allowed for skill-local bundles such as `references/api.md` |
| Cross-artifact relative | Relative link that reaches a different warehouse artifact | Invalid; rewrite to canonical form |
| Warehouse-escape relative | Relative link that resolves outside the warehouse root | Invalid; manual fix required |

The own-folder exception exists only for skills, because skills are the only
directory-shaped artifact. Contexts, knowledge files, and agents are single files,
so any non-canonical intra-warehouse link from them is malformed.

---

## Own-Folder Exception for Skills

Supporting files that ship inside a skill stay relative to the skill directory:

```markdown
See [API notes](references/api.md).
```

That is valid when the target lives at `skills/<name>/references/api.md`. Beacon keeps
this exception so bundled references, examples, templates, and scripts can travel with
the skill without pretending to be cross-artifact links.

---

## Why Project-Root Form Wins

Beacon distributes byte-identical symlinks into downstream projects. Project-root
canonical form avoids per-file path math at read time and works uniformly for every
artifact family, including agents that live outside `.agentic-beacon/artifacts/`.

Directory-relative links like `../../contexts/team-context.md` are not canonical even
when they happen to work inside the warehouse checkout. They are brittle under the
symlinked distribution model and do not generalize to agent-to-partial references.

---

## Trade-Off

Canonical links are for Beacon-aware consumers such as `abc warehouse lint`, synced
projects, and agents reading from a project root. They do not resolve in a raw GitHub
markdown view of the warehouse repository, and that is an accepted trade-off.

If you need the target in a raw repo browser, navigate by path. If you need the target
at runtime, use the canonical link.
