"""Gitignore management for Agentic Beacon.

Managed-block gitignore engine — the single cross-domain source of truth for
Beacon's .gitignore ownership.  Applies a marker-delimited managed block that
is regenerated wholesale on every run, with surgical migration of legacy
loose-line blocks.

Architecture boundary: core/ must not import from domains/ or cli/.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

# ─────────────────────────────────────────────────────────────
# Managed-block markers
# ─────────────────────────────────────────────────────────────

MANAGED_BLOCK_BEGIN = "# >>> Agentic Beacon (managed) >>>"
MANAGED_BLOCK_END = "# <<< Agentic Beacon (managed) <<<"

# Minimal set for the old-style GitignoreManager (backward compat)
GITIGNORE_ENTRIES = [
    ".agentic-beacon/config.toml",
    ".agentic-beacon/artifacts/",
    ".agentic-beacon/pending.yaml",
]

SECTION_HEADER = "# Agentic Beacon"

# ─────────────────────────────────────────────────────────────
# Tier A — unconditional root .gitignore entries
# ─────────────────────────────────────────────────────────────

TIER_A_ENTRIES = [
    ".agentic-beacon/config.toml",
    ".agentic-beacon/artifacts/",
    ".agentic-beacon/warehouse-catalog.md",
    ".agentic-beacon/pending.yaml",
    ".claude/skills/",
    ".claude/commands/",
    ".claude/agents/",
    ".opencode/skills/",
    ".opencode/command/",
    ".opencode/agents/",
]

# ─────────────────────────────────────────────────────────────
# Tier B — nested tool-dir .gitignore entries
# ─────────────────────────────────────────────────────────────

TIER_B_CLAUDE_ENTRIES = [
    "skills/",
    "scheduled_tasks.lock",
    "worktrees/",
]

TIER_B_OPENCODE_ENTRIES = [
    "skills/",
    "command/",
    "bun.lock",
    "package.json",
    "package-lock.json",
    "node_modules/",
]

# ─────────────────────────────────────────────────────────────
# Tracked-on-purpose — files that must never be git-ignored
# ─────────────────────────────────────────────────────────────

TRACKED_ON_PURPOSE = [
    ".agentic-beacon/beacon.yaml",
    ".claude/.gitignore",
    ".opencode/.gitignore",
    "CLAUDE.md",
    "opencode.json",
    ".worktreeinclude",
]

# ─────────────────────────────────────────────────────────────
# Git ignore evaluation helper
# ─────────────────────────────────────────────────────────────


def _git_would_ignore(project_root: Path, rel_path: str) -> bool:
    """True if git's ignore rules would exclude rel_path. False if not, or not a git repo."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(project_root),
                "check-ignore",
                "--no-index",
                "-q",
                rel_path,
            ],
            capture_output=True,
        )
    except (OSError, ValueError):
        return False
    return result.returncode == 0  # 0 = ignored, 1 = not ignored, 128 = not a git repo


# ─────────────────────────────────────────────────────────────
# Drift record
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GitignoreDrift:
    kind: str  # "tier_a_missing", "tier_a_incomplete", "tier_b_missing", "tier_b_incomplete", "tracked_set_ignored"
    message: str
    detail: str = ""


_LEGACY_HEADER = "# Agentic Beacon"


def _build_block_text(entries: list[str]) -> str:
    lines = [MANAGED_BLOCK_BEGIN]
    lines.extend(entries)
    lines.append(MANAGED_BLOCK_END)
    return "\n".join(lines) + "\n"


def apply_managed_block(gitignore_path: Path, entries: list[str]) -> bool:
    """Create or regenerate the marker-delimited managed block in *gitignore_path*.

    If the file already contains a managed block (bounded by MANAGED_BLOCK_BEGIN /
    MANAGED_BLOCK_END), the body between the markers is replaced wholesale.

    If no managed block exists, performs surgical migration: removes any loose
    line that exactly matches an entry, drops an emptied bare legacy header
    (``# Agentic Beacon``), then appends the managed block.

    Returns True if the file was modified, False if it was already current.
    Idempotent when re-applied with the same entries.
    """
    existing_content = ""
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text(encoding="utf-8")

    # Check for existing managed block
    begin_idx = existing_content.find(MANAGED_BLOCK_BEGIN)
    end_idx = existing_content.find(MANAGED_BLOCK_END)

    if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
        content_before = existing_content[:begin_idx]
        content_after = existing_content[end_idx + len(MANAGED_BLOCK_END) :]
        content_after = content_after.lstrip("\n")
        new_block = _build_block_text(entries)
        new_content = content_before + new_block + content_after
        if new_content == existing_content:
            return False
        gitignore_path.write_text(new_content, encoding="utf-8")
        return True

    # No managed block — surgical migration of legacy block
    existing_lines = existing_content.splitlines(keepends=True)
    entry_set = set(entries)

    # Step 1: Remove every loose line that exactly matches an entry
    filtered_lines: list[str] = []
    for line in existing_lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped in entry_set:
            continue
        filtered_lines.append(line)

    # Step 2: Drop orphaned legacy headers (no owned line beneath them)
    result_lines: list[str] = []
    i = 0
    while i < len(filtered_lines):
        line = filtered_lines[i]
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped == _LEGACY_HEADER:
            j = i + 1
            has_owned_below = False
            while j < len(filtered_lines):
                s = filtered_lines[j].rstrip("\n").rstrip("\r")
                if not s or s.startswith("#"):
                    break
                if s in entry_set:
                    has_owned_below = True
                    break
                j += 1
            if not has_owned_below:
                i += 1
                continue
        result_lines.append(line)
        i += 1

    raw = "".join(result_lines)
    block_text = _build_block_text(entries)

    stripped_raw = raw.rstrip("\n")
    new_content = (stripped_raw + "\n" + block_text) if stripped_raw else block_text
    if new_content == existing_content:
        return False
    gitignore_path.write_text(new_content, encoding="utf-8")
    return True


def read_managed_block(gitignore_path: Path) -> list[str] | None:
    """Return the entry lines of the managed block, or None if absent."""
    if not gitignore_path.exists():
        return None
    content = gitignore_path.read_text(encoding="utf-8")
    begin_idx = content.find(MANAGED_BLOCK_BEGIN)
    end_idx = content.find(MANAGED_BLOCK_END)
    if begin_idx == -1 or end_idx == -1 or end_idx <= begin_idx:
        return None
    body = content[begin_idx + len(MANAGED_BLOCK_BEGIN) : end_idx]
    entries = [
        line.rstrip("\n").rstrip("\r") for line in body.splitlines() if line.strip()
    ]
    return entries


def apply_all_gitignores(project_root: Path) -> bool:
    """Apply both tiers of gitignore managed blocks.

    Tier A is always written to the project root ``.gitignore``.
    Tier B nested files are written only when their tool directory exists:
    - ``.claude/.gitignore`` iff ``.claude/`` is a directory
    - ``.opencode/.gitignore`` iff ``.opencode/`` is a directory

    Returns True if any file was modified.
    """
    root_gitignore = project_root / ".gitignore"
    modified = apply_managed_block(root_gitignore, TIER_A_ENTRIES)

    claude_dir = project_root / ".claude"
    if claude_dir.is_dir():
        if apply_managed_block(claude_dir / ".gitignore", TIER_B_CLAUDE_ENTRIES):
            modified = True

    opencode_dir = project_root / ".opencode"
    if opencode_dir.is_dir():
        if apply_managed_block(opencode_dir / ".gitignore", TIER_B_OPENCODE_ENTRIES):
            modified = True

    return modified


def diff_gitignores(project_root: Path) -> list[GitignoreDrift]:
    """Return drift records comparing expected vs actual gitignore state.

    Read-only: does not write to any file.
    """
    drifts: list[GitignoreDrift] = []
    root_gitignore = project_root / ".gitignore"

    # Check Tier A
    tier_a_entries = read_managed_block(root_gitignore)
    if tier_a_entries is None:
        drifts.append(
            GitignoreDrift(
                kind="tier_a_missing",
                message="Tier A managed block missing from root .gitignore",
            )
        )
    elif tier_a_entries != TIER_A_ENTRIES:
        missing = set(TIER_A_ENTRIES) - set(tier_a_entries)
        extra = set(tier_a_entries) - set(TIER_A_ENTRIES)
        detail_parts = []
        if missing:
            detail_parts.append(f"Missing entries: {', '.join(sorted(missing))}")
        if extra:
            detail_parts.append(f"Extra entries: {', '.join(sorted(extra))}")
        if not missing and not extra:
            detail_parts.append("Entries reordered")
        drifts.append(
            GitignoreDrift(
                kind="tier_a_incomplete",
                message="Tier A managed block incomplete in root .gitignore",
                detail="; ".join(detail_parts),
            )
        )

    # Check Tier B
    claude_dir = project_root / ".claude"
    if claude_dir.is_dir():
        claude_gitignore = claude_dir / ".gitignore"
        b_entries = read_managed_block(claude_gitignore)
        if b_entries is None:
            drifts.append(
                GitignoreDrift(
                    kind="tier_b_missing",
                    message="Tier B managed block missing from .claude/.gitignore",
                )
            )
        elif b_entries != TIER_B_CLAUDE_ENTRIES:
            missing_b = set(TIER_B_CLAUDE_ENTRIES) - set(b_entries)
            extra_b = set(b_entries) - set(TIER_B_CLAUDE_ENTRIES)
            detail_parts = []
            if missing_b:
                detail_parts.append(f"Missing entries: {', '.join(sorted(missing_b))}")
            if extra_b:
                detail_parts.append(f"Extra entries: {', '.join(sorted(extra_b))}")
            if not missing_b and not extra_b:
                detail_parts.append("Entries reordered")
            drifts.append(
                GitignoreDrift(
                    kind="tier_b_incomplete",
                    message="Tier B managed block incomplete in .claude/.gitignore",
                    detail="; ".join(detail_parts),
                )
            )

    opencode_dir = project_root / ".opencode"
    if opencode_dir.is_dir():
        opencode_gitignore = opencode_dir / ".gitignore"
        b_entries = read_managed_block(opencode_gitignore)
        if b_entries is None:
            drifts.append(
                GitignoreDrift(
                    kind="tier_b_missing",
                    message="Tier B managed block missing from .opencode/.gitignore",
                )
            )
        elif b_entries != TIER_B_OPENCODE_ENTRIES:
            missing_b = set(TIER_B_OPENCODE_ENTRIES) - set(b_entries)
            extra_b = set(b_entries) - set(TIER_B_OPENCODE_ENTRIES)
            detail_parts = []
            if missing_b:
                detail_parts.append(f"Missing entries: {', '.join(sorted(missing_b))}")
            if extra_b:
                detail_parts.append(f"Extra entries: {', '.join(sorted(extra_b))}")
            if not missing_b and not extra_b:
                detail_parts.append("Entries reordered")
            drifts.append(
                GitignoreDrift(
                    kind="tier_b_incomplete",
                    message="Tier B managed block incomplete in .opencode/.gitignore",
                    detail="; ".join(detail_parts),
                )
            )

    # Check tracked-set — any tracked-on-purpose file currently git-ignored.
    # Uses real git ignore evaluation so glob/prefix/directory patterns
    # (.agentic-beacon/, *.yaml, .claude/) are correctly detected.
    for tracked in TRACKED_ON_PURPOSE:
        if _git_would_ignore(project_root, tracked):
            drifts.append(
                GitignoreDrift(
                    kind="tracked_set_ignored",
                    message=f"Tracked-on-purpose file would be ignored: {tracked}",
                )
            )

    return drifts


# ═════════════════════════════════════════════════════════════
# Legacy GitignoreManager (backward compat — used by connect)
# ═════════════════════════════════════════════════════════════


class GitignoreManager:
    """Manages .gitignore entries for agentic-beacon files."""

    def __init__(self, project_root: Path | str = "."):
        self.project_root = Path(project_root).resolve()
        self.gitignore_path = self.project_root / ".gitignore"

    def ensure_entries(self, entries: list[str] | None = None) -> bool:
        entries = entries or GITIGNORE_ENTRIES

        if self.gitignore_path.exists():
            existing_content = self.gitignore_path.read_text(encoding="utf-8")
            existing_lines = set(existing_content.splitlines())
        else:
            existing_content = ""
            existing_lines = set()

        missing_entries = [e for e in entries if e not in existing_lines]

        if not missing_entries:
            logger.debug("No .gitignore entries to add")
            return False

        new_lines = []

        if SECTION_HEADER not in existing_lines:
            new_lines.append(SECTION_HEADER)

        for entry in missing_entries:
            new_lines.append(entry)

        if existing_content and not existing_content.endswith("\n"):
            prefix = "\n\n"
        elif existing_content:
            prefix = "\n"
        else:
            prefix = ""

        new_content = existing_content + prefix + "\n".join(new_lines) + "\n"

        try:
            self.gitignore_path.write_text(new_content, encoding="utf-8")
            logger.debug(
                "Updated .gitignore with {} entries: {}",
                len(missing_entries),
                missing_entries,
            )
        except PermissionError as e:
            raise PermissionError(f"Cannot write to {self.gitignore_path}: {e}") from e

        return True

    def remove_entries(self, entries: list[str]) -> bool:
        if not self.gitignore_path.exists():
            return False

        existing_content = self.gitignore_path.read_text(encoding="utf-8")
        existing_lines = existing_content.splitlines()
        to_remove = set(entries)

        filtered = [line for line in existing_lines if line not in to_remove]

        if len(filtered) == len(existing_lines):
            return False

        new_content = "\n".join(filtered)
        if existing_content.endswith("\n") and filtered:
            new_content += "\n"
        elif not filtered:
            new_content = ""

        try:
            self.gitignore_path.write_text(new_content, encoding="utf-8")
            logger.debug(
                "Removed {} entries from .gitignore: {}",
                len(existing_lines) - len(filtered),
                [line for line in existing_lines if line in to_remove],
            )
        except PermissionError as e:
            raise PermissionError(f"Cannot write to {self.gitignore_path}: {e}") from e

        return True

    def has_entry(self, entry: str) -> bool:
        if not self.gitignore_path.exists():
            return False

        existing_content = self.gitignore_path.read_text(encoding="utf-8")
        existing_lines = set(existing_content.splitlines())
        return entry in existing_lines

    def verify_beacon_yaml_not_ignored(self) -> bool:
        if not self.gitignore_path.exists():
            return True

        content = self.gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        beacon_patterns = [
            "beacon.yaml",
            ".agentic-beacon/beacon.yaml",
            ".agentic-beacon/*",
            ".agentic-beacon/",
        ]

        for line in lines:
            stripped = line.strip()
            if stripped in beacon_patterns and not stripped.startswith("!"):
                return False

        return True
