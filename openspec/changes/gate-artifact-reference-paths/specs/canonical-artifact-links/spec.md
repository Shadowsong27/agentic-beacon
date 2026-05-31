## ADDED Requirements

### Requirement: Canonical intra-warehouse link form

Every inline markdown link in a warehouse artifact body whose target is another artifact in the same warehouse SHALL be written in canonical form: a project-root-relative path beginning with the literal prefix `.agentic-beacon/artifacts/`, followed by the target's warehouse-relative path. Links SHALL NOT be written relative to the linking file's directory (e.g. `../../contexts/foo.md`). A canonical link MAY carry an anchor fragment (`#heading-slug`).

The canonical form is a convention enforced by lint and resolved by Beacon-aware consumers; it does not resolve in a raw markdown renderer that lacks Beacon's resolver. The form is chosen so that an agent operating in a downstream project (cwd = project root) can read the target directly, and so that the same string is valid regardless of the linking artifact's own location — including agents distributed outside the `.agentic-beacon/artifacts/` mirror.

#### Scenario: A skill links to a context in canonical form

- **GIVEN** `skills/foo/SKILL.md` references the context `contexts/cicd-flow.md`
- **THEN** the link is written `[CI/CD](.agentic-beacon/artifacts/contexts/cicd-flow.md)`

#### Scenario: An agent links to a partial in canonical form

- **GIVEN** `agents/diligent-supervisor.md` references the partial `agent-partials/deep-review-checklist.md`
- **THEN** the link is written `[checklist](.agentic-beacon/artifacts/agent-partials/deep-review-checklist.md)`

### Requirement: Canonical link resolution rule

A consumer resolving a canonical link SHALL strip the leading `.agentic-beacon/artifacts/` prefix and treat the remainder as a path relative to the warehouse root. The target is valid if and only if that path exists as a file in the warehouse. When the link carries an anchor, the anchor SHALL be validated against the headings of the resolved target file.

In a materialized downstream project the canonical link is, by construction, the project-root-relative path of the distributed file, so resolution is equivalent to checking that `<project-root>/<link-target>` exists.

#### Scenario: Canonical link resolves to an existing warehouse file

- **GIVEN** a canonical link `.agentic-beacon/artifacts/contexts/cicd-flow.md`
- **WHEN** a consumer resolves it against a warehouse containing `contexts/cicd-flow.md`
- **THEN** resolution succeeds and points at `<warehouse>/contexts/cicd-flow.md`

#### Scenario: Canonical link resolves under the distributed layout

- **GIVEN** a project where `abc sync` has materialized `.agentic-beacon/artifacts/contexts/cicd-flow.md`
- **WHEN** a consumer reads `<project-root>/.agentic-beacon/artifacts/contexts/cicd-flow.md`
- **THEN** the file exists and is the distributed artifact

### Requirement: Link classifier

The system SHALL classify every inline markdown link target into exactly one category:

1. **Absolute URL** — contains a scheme (`://`, `mailto:`, `ftp:`): ignored.
2. **Canonical** — begins with `.agentic-beacon/artifacts/`: validated by the resolution rule.
3. **Own-folder relative** — a relative target that resolves inside the *linking skill's own directory* (skills are the only directory-shaped artifact): allowed, because bundled assets travel with the skill.
4. **Cross-artifact relative** — a relative target that resolves inside the warehouse but outside the linking artifact's own directory: a malformed link that MUST be canonical.
5. **Warehouse-escape relative** — a relative target that resolves outside the warehouse root: an unportable link.

A bare same-file anchor (`#section`, no path) is validated against the linking file's own headings.

#### Scenario: Own-folder asset link is allowed

- **GIVEN** `skills/foo/SKILL.md` contains `[api](references/api.md)` and `skills/foo/references/api.md` exists
- **THEN** the classifier marks the link own-folder and it is allowed

#### Scenario: Cross-artifact relative link is malformed

- **GIVEN** `skills/foo/SKILL.md` contains `[ctx](../../contexts/bar.md)`
- **THEN** the classifier marks the link cross-artifact-relative (malformed — must be canonical)

#### Scenario: Warehouse-escape link is flagged

- **GIVEN** `skills/foo/SKILL.md` contains `[x](../../../apps/backtest/docs/schema.md)` resolving outside the warehouse root
- **THEN** the classifier marks the link warehouse-escape

### Requirement: GitHub-compatible heading slugification

The system SHALL slugify headings using the same algorithm GitHub applies when generating anchor fragments: lowercase the heading text, remove characters that are not alphanumeric, space, or hyphen, replace spaces with hyphens, preserve consecutive hyphens produced by punctuation, and disambiguate duplicate slugs within a file by appending `-1`, `-2`, … in document order. An anchor on a link SHALL be considered resolved when its URL-decoded value equals the slug of some heading in the target file.

#### Scenario: Emoji-and-punctuation heading slugified

- **GIVEN** a target file containing the heading `## ✨ ClickhouseS3Ingestor — DLT ingestion design`
- **WHEN** the system slugifies it
- **THEN** the slug is `-clickhouses3ingestor--dlt-ingestion-design` and a link anchor with that URL-decoded value resolves

#### Scenario: Duplicate headings disambiguated

- **GIVEN** a target file with two `## Setup` headings
- **THEN** the first slugifies to `setup` and the second to `setup-1`

#### Scenario: Anchor with no matching heading is unresolved

- **GIVEN** a canonical link whose anchor is `#nonexistent-heading` and the target file has no heading slugifying to it
- **THEN** the anchor is reported unresolved
