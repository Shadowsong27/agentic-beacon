# knowledge-reference-scanning Specification

## Purpose
TBD - created by archiving change auto-pull-artifact-dependencies. Update Purpose after archive.
## Requirements
### Requirement: Scanner reads warehouse source files
The system SHALL derive knowledge references by scanning the warehouse source files, not the project's `.agentic-beacon/artifacts/` symlinks. Scanning happens before any sync-time file operations so that the needed knowledge set is computed from the warehouse as-is.

#### Scenario: Scanner operates on warehouse paths
- **WHEN** `abc sync` needs to compute the derived knowledge set
- **THEN** the scanner opens files directly from the warehouse clone (resolved via `WarehouseSettings`), not from the project's artifacts symlink tree

#### Scenario: Scanner runs before symlink creation
- **WHEN** `abc sync` executes
- **THEN** the scanner completes and produces the full derived knowledge set before any new symlinks are created in `.agentic-beacon/artifacts/knowledge/`

### Requirement: Scanner inspects adopted contexts and skills only
The system SHALL scan for knowledge references only in files that are (1) adopted contexts listed in `beacon.yaml.artifacts.contexts`, and (2) adopted skill entrypoints (`SKILL.md` files) under directories listed in `beacon.yaml.artifacts.skills`.

The system SHALL NOT scan agent files for knowledge references. Agents reach knowledge only transitively through the skills they declare as dependencies in the warehouse-level `agents/agents.yaml` manifest. Agent dependency declarations SHALL NOT carry a `contexts:` list; agents do not natively require contexts, because contexts are a project-level concern declared via `beacon.yaml.artifacts.contexts`.

The system SHALL NOT scan files outside the warehouse (e.g., the project's own `AGENTS.md`, documentation, or unrelated files).

#### Scenario: Adopted context scanned
- **WHEN** `contexts/python-standards.md` is in `beacon.yaml.artifacts.contexts`
- **THEN** the scanner reads the file and extracts all knowledge references from its markdown links

#### Scenario: Adopted skill's SKILL.md scanned
- **WHEN** `skills/python-refactor/` is in `beacon.yaml.artifacts.skills`
- **THEN** the scanner reads `skills/python-refactor/SKILL.md` and extracts knowledge references

#### Scenario: Non-entrypoint skill files not scanned
- **WHEN** a skill directory contains helper files like `scripts/run.py` or `references/guide.md`
- **THEN** the scanner does NOT inspect these files; only `SKILL.md` is scanned

#### Scenario: Agent file not scanned for knowledge
- **WHEN** an adopted agent file contains a markdown link into `knowledge/...`
- **THEN** the scanner does not treat this as a knowledge reference; the link has no effect on derived knowledge

### Requirement: Markdown link resolution and classification
The system SHALL parse every relative markdown link in a scanned file, resolve it relative to the file's own location, and classify it as a knowledge reference if and only if (1) the resolved path lies within the warehouse root, (2) the resolved path starts with `knowledge/` when expressed relative to the warehouse root, and (3) the resolved path ends in `.md`.

Links that resolve outside the warehouse (e.g., into the project or elsewhere on the filesystem) SHALL be silently ignored.

Absolute URLs (starting with `http://`, `https://`, `mailto:`, etc.) SHALL be silently ignored.

#### Scenario: Valid knowledge link from context
- **WHEN** a context at `contexts/python-standards.md` contains the link `[x](../knowledge/python-standards/lessons/foo.md)`
- **THEN** the resolved warehouse-relative path is `knowledge/python-standards/lessons/foo.md` and the scanner classifies it as a knowledge reference

#### Scenario: Valid knowledge link from skill
- **WHEN** a skill at `skills/python-refactor/SKILL.md` contains the link `[x](../../knowledge/python-standards/lessons/foo.md)`
- **THEN** the resolved warehouse-relative path is `knowledge/python-standards/lessons/foo.md` and the scanner classifies it as a knowledge reference

#### Scenario: Link outside the warehouse
- **WHEN** a scanned file contains a link like `[x](../../../other-repo/file.md)` that resolves outside the warehouse root
- **THEN** the scanner silently ignores the link

#### Scenario: HTTP URL in markdown link
- **WHEN** a scanned file contains `[x](https://example.com/foo)`
- **THEN** the scanner silently ignores the link

#### Scenario: Link to non-knowledge path
- **WHEN** a scanned file contains `[x](../contexts/other-standard.md)` which resolves inside the warehouse but not under `knowledge/`
- **THEN** the scanner does not classify it as a knowledge reference and takes no transitive action

#### Scenario: Link to non-markdown file under knowledge
- **WHEN** a scanned file contains `[x](../knowledge/diagram.png)` that resolves under `knowledge/` but does not end in `.md`
- **THEN** the scanner does not classify it as a knowledge reference

### Requirement: Derived knowledge set drives sync
The system SHALL produce a derived knowledge set as the union of all classified knowledge references from scanned files. The sync operation SHALL create one symlink per derived knowledge file, under `.agentic-beacon/artifacts/knowledge/<relative-path>`, with absolute target into the warehouse clone.

#### Scenario: Union across referrers
- **WHEN** two adopted contexts both reference `knowledge/python-standards/lessons/foo.md`
- **THEN** the derived set contains one entry for that file and sync creates exactly one symlink

#### Scenario: Knowledge pulled by a skill only
- **WHEN** no adopted context references `knowledge/testing/facts/pytest.md` but an adopted skill's SKILL.md does
- **THEN** the derived set contains the file and sync creates the symlink

#### Scenario: Missing warehouse file
- **WHEN** a scanned link resolves to `knowledge/foo/bar.md` but no such file exists in the warehouse
- **THEN** `abc sync` emits a warning naming the referrer and the missing file, but continues syncing other artifacts

### Requirement: Orphan knowledge symlinks are pruned
The system SHALL, on every `abc sync`, compute the derived knowledge set and remove any knowledge symlinks under `.agentic-beacon/artifacts/knowledge/` whose target is not in the derived set. The system SHALL also remove any empty parent directories that result from pruning.

#### Scenario: Last referrer unadopted
- **WHEN** the user unadopts the only context that referenced `knowledge/python-standards/lessons/foo.md`, then runs `abc sync`
- **THEN** the symlink `.agentic-beacon/artifacts/knowledge/python-standards/lessons/foo.md` is removed

#### Scenario: One of several referrers unadopted
- **WHEN** two contexts reference the same knowledge file and the user unadopts only one of them
- **THEN** the knowledge symlink remains in place after sync

#### Scenario: Empty parent directory cleaned up
- **WHEN** pruning removes the last file from `.agentic-beacon/artifacts/knowledge/python-standards/lessons/`
- **THEN** the empty `lessons/` directory is removed; the parent `python-standards/` is also removed if it becomes empty
