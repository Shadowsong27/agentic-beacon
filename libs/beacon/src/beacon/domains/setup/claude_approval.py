"""Approve external context imports for Claude Code in the user's Claude config.

Each context in ``.agentic-beacon/artifacts/contexts/`` is a symlink into the
warehouse, so Claude Code treats an ``@`` import of it as external. Claude Code
loads such an import only when ``~/.claude.json`` holds
``projects["<project root>"].hasClaudeMdExternalIncludesApproved = true``.

The flag is set for the main checkout root, so imports also load from a
subdirectory and from a git worktree of the same repository. Only the current
user's config is touched. The file is never created.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

APPROVAL_FLAG = "hasClaudeMdExternalIncludesApproved"


class ApprovalStatus(StrEnum):
    """Outcome of an approval check or write."""

    APPROVED = "approved"
    ALREADY_APPROVED = "already_approved"
    NOT_APPROVED = "not_approved"
    NOT_NEEDED = "not_needed"
    CLAUDE_NOT_INSTALLED = "claude_not_installed"
    CONFIG_MISSING = "config_missing"
    CONFIG_UNREADABLE = "config_unreadable"
    CONFIG_MALFORMED = "config_malformed"
    WRITE_FAILED = "write_failed"


_OK_STATUSES = frozenset(
    {
        ApprovalStatus.APPROVED,
        ApprovalStatus.ALREADY_APPROVED,
        ApprovalStatus.NOT_NEEDED,
        ApprovalStatus.CLAUDE_NOT_INSTALLED,
    }
)


@dataclass(frozen=True)
class ApprovalResult:
    """Outcome of an approval check, with the data needed to report it."""

    status: ApprovalStatus
    project_key: str
    config_path: Path
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in _OK_STATUSES

    @property
    def message(self) -> str:
        manual = f'Set projects["{self.project_key}"].{APPROVAL_FLAG} to true by hand'
        match self.status:
            case ApprovalStatus.APPROVED:
                return (
                    "Approved external context imports for Claude Code in "
                    f"{self.config_path} ({self.project_key})"
                )
            case ApprovalStatus.ALREADY_APPROVED:
                return f"External context imports already approved ({self.project_key})"
            case ApprovalStatus.NOT_APPROVED:
                return (
                    "External context imports not approved for Claude Code in "
                    f"{self.config_path} ({self.project_key})"
                )
            case ApprovalStatus.NOT_NEEDED:
                return "No wired contexts — nothing to approve for Claude Code"
            case ApprovalStatus.CLAUDE_NOT_INSTALLED:
                return (
                    "Claude Code not found — skipped approving external context imports"
                )
            case ApprovalStatus.CONFIG_MISSING:
                return (
                    f"{self.config_path} not found — not created. "
                    "Start Claude Code once, then re-run abc sync"
                )
            case ApprovalStatus.CONFIG_UNREADABLE | ApprovalStatus.CONFIG_MALFORMED:
                return (
                    f"{self.config_path} could not be read ({self.detail}) — "
                    f"left unchanged. {manual}"
                )
            case ApprovalStatus.WRITE_FAILED:
                return (
                    f"{self.config_path} could not be written ({self.detail}) — "
                    f"left unchanged. {manual}"
                )


@dataclass(frozen=True)
class _Inspection:
    """Result of inspection plus the parsed config needed for a write."""

    result: ApprovalResult
    data: dict[str, Any] | None
    text: str


def claude_config_path() -> Path:
    """Return the current user's Claude Code config file (``.claude.json``)."""
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if config_dir:
        return Path(config_dir) / ".claude.json"
    return Path.home() / ".claude.json"


def has_wired_contexts(project_root: Path) -> bool:
    """Return True when AGENTS.md imports at least one beacon context."""
    # Local import: wiring imports this module at load time.
    from beacon.domains.setup.wiring import ARTIFACT_REF_PREFIX as ref_prefix

    agents_md = project_root / "AGENTS.md"
    if not agents_md.is_file():
        return False
    try:
        text = agents_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    prefix = "@" + ref_prefix
    return any(line.strip().startswith(prefix) for line in text.splitlines())


def resolve_claude_project_root(project_root: Path) -> Path:
    """Return the main checkout root for ``project_root``.

    For a linked git worktree this is the main checkout. Outside git, for a
    bare repository, or for a submodule, it is ``project_root`` itself.
    """
    fallback = project_root.resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return fallback
    if proc.returncode != 0:
        return fallback
    common_dir = (project_root / proc.stdout.strip()).resolve()
    if common_dir.name == ".git":
        return common_dir.parent
    return fallback


def _inspect(project_root: Path) -> _Inspection:
    config_path = claude_config_path()
    key = str(resolve_claude_project_root(project_root))

    def outcome(status: ApprovalStatus, detail: str = "") -> ApprovalResult:
        return ApprovalResult(
            status=status, project_key=key, config_path=config_path, detail=detail
        )

    empty = _Inspection(result=outcome(ApprovalStatus.NOT_NEEDED), data=None, text="")
    if not has_wired_contexts(project_root):
        return empty

    if not os.path.lexists(config_path):
        if shutil.which("claude") is None:
            return _Inspection(
                result=outcome(ApprovalStatus.CLAUDE_NOT_INSTALLED), data=None, text=""
            )
        return _Inspection(
            result=outcome(ApprovalStatus.CONFIG_MISSING), data=None, text=""
        )

    try:
        raw = config_path.read_bytes()
    except OSError as exc:
        return _Inspection(
            result=outcome(ApprovalStatus.CONFIG_UNREADABLE, str(exc)),
            data=None,
            text="",
        )

    def malformed(reason: str) -> _Inspection:
        return _Inspection(
            result=outcome(ApprovalStatus.CONFIG_MALFORMED, reason), data=None, text=""
        )

    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except ValueError as exc:
        return malformed(str(exc))
    if not isinstance(data, dict):
        return malformed("top-level value is not a JSON object")
    projects = data.get("projects", {})
    if not isinstance(projects, dict):
        return malformed('"projects" is not a JSON object')
    entry = projects.get(key, {})
    if not isinstance(entry, dict):
        return malformed(f'projects["{key}"] is not a JSON object')

    if entry.get(APPROVAL_FLAG) is True:
        status = ApprovalStatus.ALREADY_APPROVED
    else:
        status = ApprovalStatus.NOT_APPROVED
    return _Inspection(result=outcome(status), data=data, text=text)


def inspect_claude_approval(project_root: Path) -> ApprovalResult:
    """Report whether Claude Code is approved to load external imports. Read-only."""
    return _inspect(project_root).result


def _write_json_atomic(
    config_path: Path, data: dict[str, Any], *, trailing_newline: bool
) -> None:
    """Replace ``config_path`` (following symlinks) with ``data`` atomically."""
    target = config_path.resolve()
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if trailing_newline:
        text += "\n"
    mode = stat.S_IMODE(target.stat().st_mode)
    tmp = tempfile.NamedTemporaryFile(
        "w",
        dir=target.parent,
        delete=False,
        prefix=".claude.json.",
        suffix=".tmp",
        encoding="utf-8",
    )
    tmp_path = Path(tmp.name)
    try:
        with tmp:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, target)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def ensure_claude_approval(project_root: Path) -> ApprovalResult:
    """Set the approval flag for the project root when wired contexts need it.

    Writes only when the flag is missing. Never creates the config file.
    """
    inspection = _inspect(project_root)
    result = inspection.result
    if result.status is not ApprovalStatus.NOT_APPROVED or inspection.data is None:
        if not result.ok:
            logger.warning(result.message)
        return result

    data = inspection.data
    data.setdefault("projects", {}).setdefault(result.project_key, {})[
        APPROVAL_FLAG
    ] = True
    try:
        _write_json_atomic(
            result.config_path,
            data,
            trailing_newline=inspection.text.endswith("\n"),
        )
    except OSError as exc:
        failed = ApprovalResult(
            status=ApprovalStatus.WRITE_FAILED,
            project_key=result.project_key,
            config_path=result.config_path,
            detail=str(exc),
        )
        logger.warning(failed.message)
        return failed

    approved = ApprovalResult(
        status=ApprovalStatus.APPROVED,
        project_key=result.project_key,
        config_path=result.config_path,
    )
    logger.info(approved.message)
    return approved
