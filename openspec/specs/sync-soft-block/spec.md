# sync-soft-block Specification

## Purpose
TBD - created by archiving change global-agent-artifact-type. Update Purpose after archive.
## Requirements
### Requirement: abc sync warns before overwriting locally-modified files
When `abc sync` is about to overwrite a local artifact file with warehouse content and the local file content differs from the warehouse file, the CLI SHALL present a soft block: list all conflicting files, then prompt once with y/N before proceeding. On `y`, all differing files are overwritten. On `N`, no files are written and the sync exits cleanly.

#### Scenario: No conflicts — proceeds silently
- **WHEN** all local artifact files are identical to their warehouse counterparts
- **THEN** sync proceeds without any warning or prompt

#### Scenario: One or more conflicts — interactive soft block
- **WHEN** at least one local artifact file differs from the warehouse file AND the session is interactive
- **THEN** the CLI lists all conflicting file paths, prompts "Overwrite local changes? [y/N]", overwrites all on `y`, skips all writes on `N`

#### Scenario: Fresh file — no conflict
- **WHEN** a local artifact file does not yet exist (first sync)
- **THEN** the file is copied without any prompt

#### Scenario: Conflicts in non-interactive mode — hard block
- **WHEN** at least one local artifact file differs from warehouse AND the session is non-interactive (no TTY) AND neither `--preserve` nor `--force` is passed
- **THEN** the CLI exits with a non-zero status and prints an error listing conflicting files; no files are written

#### Scenario: --preserve flag — skip conflicting files
- **WHEN** `abc sync --preserve` is run AND local files differ from warehouse
- **THEN** differing files are skipped silently (existing --preserve behaviour, unchanged)

#### Scenario: --force flag — overwrite without prompt
- **WHEN** `abc sync --force` is run AND local files differ from warehouse
- **THEN** all files are overwritten without prompting, regardless of interactive mode

### Requirement: abc install applies the same soft-block model
`abc install` for all artifact types (knowledge, contexts, skills, agents) SHALL apply the same soft-block logic as `abc sync` when the target file already exists with different content.

#### Scenario: abc install — target identical
- **WHEN** `abc install` targets a file with identical content to the warehouse
- **THEN** the file is skipped (no-op), no prompt

#### Scenario: abc install — target differs, interactive
- **WHEN** `abc install` targets a file with different content AND session is interactive
- **THEN** the CLI warns and prompts y/N; on `y` overwrites, on `N` skips

#### Scenario: abc install — target differs, non-interactive, no flags
- **WHEN** `abc install` targets a file with different content AND session is non-interactive AND neither `--preserve` nor `--force` is set
- **THEN** exits with non-zero status; no files written

### Requirement: Skill live-dir wiring respects soft block
When `abc install skills/<name>` wires a skill to live agent directories (`.opencode/skills/`, `.claude/skills/`), the soft-block check SHALL apply to the live-dir destination as well as the artifacts snapshot.

#### Scenario: Live-dir skill file differs — soft block applies
- **WHEN** the live-dir skill file differs from the warehouse skill file AND session is interactive
- **THEN** the CLI warns and prompts before overwriting the live-dir file

### Requirement: Bundled skills are exempt from soft block
`_install_bundled_skills_globally()` installs ABC-package-managed skills to global agent dirs. These SHALL always overwrite on diff without prompting — they are not user content.

#### Scenario: Bundled skill differs — silent overwrite
- **WHEN** a bundled skill file at `~/.config/opencode/skills/` or `~/.claude/skills/` differs from the bundled package version
- **THEN** the file is overwritten silently without any prompt
