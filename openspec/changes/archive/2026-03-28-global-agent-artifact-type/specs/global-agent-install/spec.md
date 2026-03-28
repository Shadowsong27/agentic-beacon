## ADDED Requirements

### Requirement: Install routes agents to global directories
When `abc install agents/<name>.md` is invoked, the CLI SHALL detect globally available coding agent tools (OpenCode and Claude Code) by inspecting the developer's home directory and install the agent markdown file to each detected tool's global agents directory. No `beacon.yaml` entry is written.

#### Scenario: Both tools detected
- **WHEN** `~/.config/opencode/` exists AND `~/.claude/` exists
- **THEN** the agent file is installed to `~/.config/opencode/agents/<name>.md` AND `~/.claude/agents/<name>.md`

#### Scenario: Only OpenCode detected
- **WHEN** `~/.config/opencode/` exists AND `~/.claude/` does NOT exist
- **THEN** the agent file is installed to `~/.config/opencode/agents/<name>.md` only

#### Scenario: Only Claude Code detected
- **WHEN** `~/.config/opencode/` does NOT exist AND `~/.claude/` exists
- **THEN** the agent file is installed to `~/.claude/agents/<name>.md` only

#### Scenario: No agent tools detected
- **WHEN** neither `~/.config/opencode/` nor `~/.claude/` exists
- **THEN** the CLI prints a warning that no global agent tools were detected and no files are written

### Requirement: Install creates parent agent directories
The CLI SHALL create `~/.config/opencode/agents/` and `~/.claude/agents/` if they do not yet exist before writing the agent file.

#### Scenario: Missing target directory is created
- **WHEN** the detected tool's agents directory does not exist
- **THEN** the directory is created automatically before the file is written

### Requirement: Install applies soft block when content differs
Agent install follows the same soft-block model as `abc sync` and `abc install` for other artifact types (see `sync-soft-block` capability). If the target agent file already exists with **different** content, the CLI SHALL warn and prompt for confirmation before overwriting. If content is identical, the install is a no-op.

#### Scenario: Identical content — no-op
- **WHEN** the target agent file already exists with content identical to the warehouse file
- **THEN** the file is not written and no warning is printed

#### Scenario: Different content — soft block
- **WHEN** the target agent file exists with content that differs from the warehouse file AND the session is interactive
- **THEN** the CLI prints a warning listing the conflicting file and prompts y/N; on `y` the file is overwritten; on `N` the file is skipped

#### Scenario: Different content — non-interactive hard block
- **WHEN** the target agent file exists with content that differs AND the session is non-interactive (no TTY) AND neither `--preserve` nor `--force` is set
- **THEN** the CLI exits with a non-zero status and prints an error listing the conflicting file

#### Scenario: Different content — --preserve skips
- **WHEN** `--preserve` is passed AND the target agent file differs from the warehouse
- **THEN** the file is skipped without prompting

#### Scenario: Different content — --force overwrites
- **WHEN** `--force` is passed AND the target agent file differs from the warehouse
- **THEN** the file is overwritten without prompting

#### Scenario: File does not exist — fresh install
- **WHEN** no agent file exists at the target path
- **THEN** the warehouse file is written to the target path without any prompt

### Requirement: Install does not modify beacon.yaml
Agent install SHALL NOT add any entry to `beacon.yaml` under any artifact type key.

#### Scenario: beacon.yaml unchanged after agent install
- **WHEN** `abc install agents/<name>.md` completes successfully
- **THEN** the project's `beacon.yaml` (if present) is identical to before the command was run

### Requirement: Global agent detection uses a dedicated helper
A dedicated function `_detect_agents_global()` SHALL be introduced in `cli.py`, separate from the existing `_detect_agents(project_root)`. It MUST check home-directory paths only: `~/.config/opencode/` and `~/.claude/`.

#### Scenario: Global detection independent of project
- **WHEN** `_detect_agents_global()` is called from any working directory
- **THEN** it returns tools based solely on the existence of `~/.config/opencode/` and `~/.claude/`, not on any project file
