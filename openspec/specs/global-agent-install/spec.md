# global-agent-install Specification

## Purpose
TBD - created by archiving change global-agent-artifact-type. Update Purpose after archive.
## Requirements
### Requirement: Install routes agents to global directories
When `abc install agents/<name>.md` is invoked, the CLI SHALL detect globally available coding agent tools (OpenCode and Claude Code) by inspecting the developer's home directory and create a symlink from each detected tool's global agents directory to the warehouse agent file. No `beacon.yaml` entry is written.

#### Scenario: Both tools detected
- **WHEN** `~/.config/opencode/` exists AND `~/.claude/` exists
- **THEN** symlinks are created at `~/.config/opencode/agents/<name>.md` AND `~/.claude/agents/<name>.md`

#### Scenario: Only OpenCode detected
- **WHEN** `~/.config/opencode/` exists AND `~/.claude/` does NOT exist
- **THEN** a symlink is created at `~/.config/opencode/agents/<name>.md` only

#### Scenario: Only Claude Code detected
- **WHEN** `~/.config/opencode/` does NOT exist AND `~/.claude/` exists
- **THEN** a symlink is created at `~/.claude/agents/<name>.md` only

#### Scenario: No agent tools detected
- **WHEN** neither `~/.config/opencode/` nor `~/.claude/` exists
- **THEN** the CLI prints a warning that no global agent tools were detected and no files are written

### Requirement: Install creates parent agent directories
The CLI SHALL create `~/.config/opencode/agents/` and `~/.claude/agents/` if they do not yet exist before creating the symlink.

#### Scenario: Missing target directory is created
- **WHEN** the detected tool's agents directory does not exist
- **THEN** the directory is created automatically before the symlink is created

### Requirement: Install applies soft block when content differs
Agent install follows the same soft-block model as `abc sync` and `abc install` for other artifact types (see `sync-soft-block` capability). If the target agent file already exists with **different** content, the CLI SHALL warn and prompt for confirmation before replacing it with a warehouse symlink. If the target is already a symlink to the warehouse file, the install is a no-op.

#### Scenario: Identical content — no-op
- **WHEN** the target agent file is already a symlink to the warehouse file
- **THEN** the symlink is left unchanged and no warning is printed

#### Scenario: Different content — soft block
- **WHEN** the target agent file exists with content that differs from the warehouse file AND the session is interactive
- **THEN** the CLI prints a warning listing the conflicting file and prompts y/N; on `y` the file is replaced with a warehouse symlink; on `N` the file is skipped

#### Scenario: Different content — non-interactive hard block
- **WHEN** the target agent file exists with content that differs AND the session is non-interactive (no TTY) AND neither `--preserve` nor `--force` is set
- **THEN** the CLI exits with a non-zero status and prints an error listing the conflicting file

#### Scenario: Different content — --preserve skips
- **WHEN** `--preserve` is passed AND the target agent file differs from the warehouse
- **THEN** the file is skipped without prompting

#### Scenario: Different content — --force overwrites
- **WHEN** `--force` is passed AND the target agent file differs from the warehouse
- **THEN** the file is replaced with a warehouse symlink without prompting

#### Scenario: File does not exist — fresh install
- **WHEN** no agent file exists at the target path
- **THEN** a symlink to the warehouse file is created at the target path without any prompt

#### Scenario: Identical legacy copy is migrated
- **WHEN** the target agent file already exists as a regular file with content identical to the warehouse file
- **THEN** the file is replaced with a symlink to the warehouse file without prompting

#### Scenario: Broken symlink is repaired
- **WHEN** the target agent path is a broken symlink
- **THEN** the symlink is repaired to point at the warehouse file without prompting

### Requirement: Install does not modify beacon.yaml
`abc install agents/<name>.md` SHALL NOT add any entry to `beacon.yaml` under any artifact type key. This command remains available as a power-user escape hatch for global agent installation without project-level declaration; the project-scoped entry point for agent adoption is `abc adopt` (see `artifact-adoption` capability).

#### Scenario: beacon.yaml unchanged after agent install
- **WHEN** `abc install agents/<name>.md` completes successfully
- **THEN** the project's `beacon.yaml` (if present) is identical to before the command was run — `artifacts.agents` is not modified

#### Scenario: Global install coexists with project declaration
- **WHEN** a user runs `abc install agents/spec-planner.md` in a project where `beacon.yaml.artifacts.agents` does NOT include `agents/spec-planner.md`
- **THEN** the agent is globally symlinked and `beacon.yaml` is unchanged; a subsequent `abc adopt` invocation will show the agent as an unadopted candidate that the user can opt into declaring

### Requirement: Global agent detection uses a dedicated helper
A dedicated function `_detect_agents_global()` SHALL be introduced in `cli.py`, separate from the existing `_detect_agents(project_root)`. It MUST check home-directory paths only: `~/.config/opencode/` and `~/.claude/`.

#### Scenario: Global detection independent of project
- **WHEN** `_detect_agents_global()` is called from any working directory
- **THEN** it returns tools based solely on the existence of `~/.config/opencode/` and `~/.claude/`, not on any project file
