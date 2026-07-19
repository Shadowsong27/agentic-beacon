"""Gitignore management for Agentic Beacon.

Managed-block gitignore engine — the single cross-domain source of truth for
Beacon's .gitignore ownership.  Applies a marker-delimited managed block that
is regenerated wholesale on every run, with surgical migration of legacy
loose-line blocks.

Architecture boundary: core/ must not import from domains/ or cli/.
"""

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
    filtered_lines: list[str] = []
    skip_until: int | None = None
    for i, line in enumerate(existing_lines):
        if skip_until is not None:
            if i < skip_until:
                continue
            skip_until = None
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped != _LEGACY_HEADER:
            filtered_lines.append(line)
            continue
        j = i + 1
        owned_removed = False
        while j < len(existing_lines):
            s = existing_lines[j].rstrip("\n").rstrip("\r")
            if not s or s.startswith("#"):
                break
            if s in entry_set:
                owned_removed = True
                j += 1
            else:
                break
        if owned_removed:
            skip_until = j
            continue
        filtered_lines.append(line)
        for k in range(i + 1, j):
            filtered_lines.append(existing_lines[k])
        skip_until = j

    raw = "".join(filtered_lines)
    block_text = _build_block_text(entries)

    new_content = raw.rstrip("\n") + "\n" + block_text
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


def apply_all_gitignores(project_root: Path) -> None:
    """Apply both tiers of gitignore managed blocks.

    Tier A is always written to the project root ``.gitignore``.
    Tier B nested files are written only when their tool directory exists:
    - ``.claude/.gitignore`` iff ``.claude/`` is a directory
    - ``.opencode/.gitignore`` iff ``.opencode/`` is a directory
    """
    root_gitignore = project_root / ".gitignore"
    apply_managed_block(root_gitignore, TIER_A_ENTRIES)

    claude_dir = project_root / ".claude"
    if claude_dir.is_dir():
        apply_managed_block(claude_dir / ".gitignore", TIER_B_CLAUDE_ENTRIES)

    opencode_dir = project_root / ".opencode"
    if opencode_dir.is_dir():
        apply_managed_block(opencode_dir / ".gitignore", TIER_B_OPENCODE_ENTRIES)


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
    else:
        tier_a_set = set(tier_a_entries)
        expected_a = set(TIER_A_ENTRIES)
        missing = expected_a - tier_a_set
        if missing:
            drifts.append(
                GitignoreDrift(
                    kind="tier_a_incomplete",
                    message="Tier A managed block incomplete in root .gitignore",
                    detail=f"Missing entries: {', '.join(sorted(missing))}",
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
        else:
            expected_b = set(TIER_B_CLAUDE_ENTRIES)
            missing_b = expected_b - set(b_entries)
            if missing_b:
                drifts.append(
                    GitignoreDrift(
                        kind="tier_b_incomplete",
                        message="Tier B managed block incomplete in .claude/.gitignore",
                        detail=f"Missing entries: {', '.join(sorted(missing_b))}",
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
        else:
            expected_b = set(TIER_B_OPENCODE_ENTRIES)
            missing_b = expected_b - set(b_entries)
            if missing_b:
                drifts.append(
                    GitignoreDrift(
                        kind="tier_b_incomplete",
                        message="Tier B managed block incomplete in .opencode/.gitignore",
                        detail=f"Missing entries: {', '.join(sorted(missing_b))}",
                    )
                )

    # Check tracked-set — any tracked-on-purpose file currently git-ignored
    if root_gitignore.exists():
        content = root_gitignore.read_text(encoding="utf-8")
        for tracked in TRACKED_ON_PURPOSE:
            tracked_short = Path(tracked).name
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == tracked_short or stripped == tracked:
                    if not stripped.startswith("!"):
                        drifts.append(
                            GitignoreDrift(
                                kind="tracked_set_ignored",
                                message=f"Tracked-on-purpose file would be ignored: {tracked}",
                            )
                        )
                        break

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
