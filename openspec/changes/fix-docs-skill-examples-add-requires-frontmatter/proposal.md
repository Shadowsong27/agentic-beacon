# fix-docs-skill-examples-add-requires-frontmatter

## Why

Two user-facing guides (`site-docs/guides/warehouse-creation.md` and `site-docs/guides/creating-skills.md`) ship SKILL.md template examples that omit the `requires:` YAML frontmatter. The skill manifest schema treats `requires:` as a first-class field — `site-docs/reference/beacon-yaml.md` (lines ~77-87) and `site-docs/concepts/artifact-types.md` (lines ~85-93) both document it as expected metadata, and the warehouse manifest scanner reads it to drive transitive skill dependency resolution.

Users who copy the example SKILL.md templates from these guides produce skills that lack the dependency-resolution metadata. The skills themselves are still valid — `requires:` is optional in the schema and the scanner silently treats missing fields as empty — but the templates are misleading because they teach a pattern that omits the documented authoring contract.

(Note: if `requires:` truly were mandatory, `abc sync` would reject these examples outright. The audit characterised the missing field as "mandatory"; verification against `libs/beacon/src/beacon/core/manifest/skill.py` is required before claiming hard rejection. The fix is the same either way: align the examples with the documented authoring contract.)

## What Changes

- **site-docs/guides/warehouse-creation.md (around lines 79, 102-148):** Every SKILL.md frontmatter example gains a `requires:` block at the same indentation level as `name:`, `description:`, etc. Use realistic example dependencies (e.g. `contexts: [python-standards]`) drawn from the guide's own context.
- **site-docs/guides/creating-skills.md (around lines 40-92, 100-144, 180-211):** Same treatment — every SKILL.md frontmatter example gains `requires:`. Where the guide already mentions that skills can depend on contexts/knowledge, surface the field in the template.
- **Both guides:** Add a one-line caption near each touched example explaining what `requires:` does. Do NOT introduce new sections or rewrite surrounding prose.

## Out of Scope

- Any change to the schema, scanner, or manifest validation code.
- `docs/` files — those are internal design notes and may legitimately use simplified examples.
- `site-docs/reference/beacon-yaml.md` and `site-docs/concepts/artifact-types.md` — these already document `requires:` correctly.
- The `concepts/how-it-works.md` example skill snippet, unless it also drops `requires:`.

## Acceptance Criteria

After this change:

1. Every YAML frontmatter block introduced by ` ```yaml` followed by `name:` in `site-docs/guides/warehouse-creation.md` and `site-docs/guides/creating-skills.md` contains a `requires:` key.
2. Each `requires:` value uses realistic content (at minimum an empty list `[]` or an example `contexts:` / `knowledge:` list).
3. The captions around the templates explain — in one short sentence — what `requires:` declares.
4. Commit message: `docs: add requires: frontmatter to SKILL.md examples in user guides`. Conventional Commits.
