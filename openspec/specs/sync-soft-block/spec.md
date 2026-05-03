# sync-soft-block Specification

## Purpose

Prevent silent overwrites of user-modified artifact files during installation by presenting a soft block (interactive prompt) when `abc install` would otherwise clobber locally-modified content. The soft block extends to skill live-dir wiring.

> Historical context: earlier versions of this spec also covered `abc sync`. `abc sync` no longer copies files — it creates symlinks into the warehouse clone (see `openspec/specs/symlink-based-sync/spec.md` and `knowledge/decisions/single-warehouse-write-entrypoint.md`), so the overwrite-collision model does not apply. The soft block remains relevant for `abc install`, which still materializes real files in target locations outside the warehouse tree (global agent dirs, opencode/claude skill dirs).

## Requirements

### Requirement: abc install applies the soft-block model

`abc install` for all artifact types (knowledge, contexts, skills, agents) SHALL apply soft-block logic when the target file already exists with different content.

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
