"""Read warehouse items at a commit as data (abc context show, agent show, ...).

Reads committed git objects only. The working tree is never consulted, so the
output for a given ref does not change with uncommitted edits.

Missing items raise ItemMissingError (exit 3 at the CLI). An unreadable source
raises WarehouseReadError (exit 1). The two never share a code.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from beacon.core.dependencies.frontmatter import split_frontmatter
from beacon.domains.warehouse.context_index import (
    ContextIndexError,
    is_context_path,
    resolve_index_warehouse,
)
from beacon.domains.warehouse.warehouse_path import (
    WarehousePathMissing,
    WarehousePathNotARepo,
    WarehousePathOK,
    validate_warehouse_path,
)
from beacon.utils.git import list_tree_paths, read_blob, resolve_commit

CONTEXTS_DIR = "contexts/"
AGENTS_DIR = "agents/"

_BOARD_OR_DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_DECISION_RULES_HEADING = "## Decision rules"


class WarehouseReadError(Exception):
    """A warehouse item cannot be read. The message names the cause."""


class ItemMissingError(WarehouseReadError):
    """One or more requested items are absent at the commit."""

    def __init__(self, sha: str, missing: list[str]) -> None:
        self.sha = sha
        self.missing = missing
        super().__init__(f"missing at {sha}: {', '.join(missing)}")


class InvalidNameError(ValueError):
    """A board, domain, context or agent name fails the name rules."""


@dataclass
class FileRecord:
    """One file read at a commit. ``warning`` is reported on stderr, not in JSON."""

    name: str
    path: str
    text: str
    frontmatter: dict | None
    body: str
    warning: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "text": self.text,
            "frontmatter": self.frontmatter,
            "body": self.body,
        }


@dataclass
class ContextsResult:
    warehouse: str
    ref: str
    sha: str
    contexts: list[FileRecord]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "contexts": [record.to_dict() for record in self.contexts],
        }


@dataclass
class PolicyResult:
    warehouse: str
    ref: str
    sha: str
    board: str
    policy: FileRecord
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "board": self.board,
            "policy": self.policy.to_dict(),
        }


@dataclass
class ProfileResult:
    warehouse: str
    ref: str
    sha: str
    domain: str
    profile: FileRecord
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "domain": self.domain,
            "profile": self.profile.to_dict(),
        }


@dataclass
class AgentsResult:
    warehouse: str
    ref: str
    sha: str
    agents: list[FileRecord]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "agents": [record.to_dict() for record in self.agents],
        }


@dataclass
class DecisionRule:
    """The ``## Decision rules`` section of one context."""

    name: str
    path: str
    body: str

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path, "body": self.body}


@dataclass
class DecisionRulesResult:
    warehouse: str
    ref: str
    sha: str
    rules: list[DecisionRule]

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "rules": [rule.to_dict() for rule in self.rules],
        }


# ---------------------------------------------------------------------------
# Name checks (design D4)
# ---------------------------------------------------------------------------


def check_board_or_domain(value: str, kind: str) -> str:
    """Return ``value`` if it is a valid board or domain name, else raise."""
    if not _BOARD_OR_DOMAIN_RE.match(value):
        raise InvalidNameError(
            f"invalid {kind} '{value}': use letters, digits, '-' and '_', "
            "starting with a letter or digit"
        )
    return value


def check_context_name(name: str) -> str:
    """Return ``name`` if it is a valid context name, else raise.

    A context name is one or more ``/``-separated segments, with no ``.md`` suffix.
    """
    if name.endswith(".md"):
        raise InvalidNameError(f"invalid context name '{name}': drop the '.md' suffix")
    for segment in name.split("/"):
        if segment == ".." or not _SEGMENT_RE.match(segment):
            raise InvalidNameError(f"invalid context name '{name}'")
    return name


def check_agent_name(name: str) -> str:
    """Return ``name`` if it is a valid agent name, else raise."""
    if name.endswith(".md") or "/" in name or not _SEGMENT_RE.match(name):
        raise InvalidNameError(f"invalid agent name '{name}'")
    return name


# ---------------------------------------------------------------------------
# Source access
# ---------------------------------------------------------------------------


def resolve_repo_root(repo: Path) -> Path:
    """Return the git root for ``repo``, or raise WarehouseReadError."""
    result = validate_warehouse_path(repo)
    if isinstance(result, WarehousePathMissing):
        raise WarehouseReadError(f"path does not exist: {result.path}")
    if isinstance(result, WarehousePathNotARepo):
        raise WarehouseReadError(
            f"not a git repository: {result.path} ({result.reason})"
        )
    assert isinstance(result, WarehousePathOK)
    return result.path


@dataclass
class _Source:
    """A warehouse at a commit, with the listing of one directory."""

    warehouse: Path
    ref: str
    sha: str
    listing: list[str]


def _open_directory(
    warehouse: Path | None, ref: str, cwd: Path, directory: str
) -> _Source:
    """Resolve the warehouse and ref, then list ``directory`` at the commit."""
    try:
        root = resolve_index_warehouse(warehouse, cwd)
    except ContextIndexError as exc:
        raise WarehouseReadError(str(exc)) from exc

    sha = resolve_commit(root, ref)
    if sha is None:
        raise WarehouseReadError(f"ref '{ref}' not found in warehouse {root}")

    listing = list_tree_paths(root, sha, directory)
    if listing is None:
        raise WarehouseReadError(f"git ls-tree failed for {sha} in warehouse {root}")
    if not listing:
        raise WarehouseReadError(
            f"no {directory.rstrip('/')}/ directory at {sha} in warehouse {root}"
        )
    return _Source(warehouse=root, ref=ref, sha=sha, listing=listing)


def _decode_blob(source: _Source, path: str) -> str:
    blob = read_blob(source.warehouse, source.sha, path)
    if blob is None:
        raise WarehouseReadError(f"git show failed for {path} at {source.sha}")
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WarehouseReadError(f"{path} at {source.sha} is not valid UTF-8") from exc


def _read_record(source: _Source, name: str, path: str) -> FileRecord:
    text = _decode_blob(source, path)
    split = split_frontmatter(text)
    warning = f"{path}: {split.warning}" if split.warning else None
    return FileRecord(
        name=name,
        path=path,
        text=text,
        frontmatter=split.frontmatter,
        body=split.body,
        warning=warning,
    )


def _read_named_files(
    source: _Source, items: list[tuple[str, str]]
) -> list[FileRecord]:
    """Read ``(name, path)`` items. Every missing path is reported together."""
    present = set(source.listing)
    missing = [path for _, path in items if path not in present]
    if missing:
        raise ItemMissingError(source.sha, missing)
    return [_read_record(source, name, path) for name, path in items]


def _warnings(records: list[FileRecord]) -> list[str]:
    return [record.warning for record in records if record.warning is not None]


# ---------------------------------------------------------------------------
# Public reads
# ---------------------------------------------------------------------------


def read_contexts(
    warehouse: Path | None, ref: str, cwd: Path, names: list[str]
) -> ContextsResult:
    """Read the contexts ``names`` at ``ref``, in the order given, each once."""
    unique = list(dict.fromkeys(check_context_name(name) for name in names))
    source = _open_directory(warehouse, ref, cwd, CONTEXTS_DIR)
    items = [(name, f"{CONTEXTS_DIR}{name}.md") for name in unique]
    records = _read_named_files(source, items)
    return ContextsResult(
        warehouse=str(source.warehouse),
        ref=ref,
        sha=source.sha,
        contexts=records,
        warnings=_warnings(records),
    )


def read_intake_policy(
    warehouse: Path | None, ref: str, cwd: Path, board: str
) -> PolicyResult:
    """Read ``contexts/intake-policy-<board>.md`` at ``ref``."""
    check_board_or_domain(board, "board")
    name = f"intake-policy-{board}"
    source = _open_directory(warehouse, ref, cwd, CONTEXTS_DIR)
    (record,) = _read_named_files(source, [(name, f"{CONTEXTS_DIR}{name}.md")])
    return PolicyResult(
        warehouse=str(source.warehouse),
        ref=ref,
        sha=source.sha,
        board=board,
        policy=record,
        warnings=_warnings([record]),
    )


def read_operate_profile(
    warehouse: Path | None, ref: str, cwd: Path, domain: str
) -> ProfileResult:
    """Read ``contexts/operate-<domain>.md`` at ``ref``."""
    check_board_or_domain(domain, "domain")
    name = f"operate-{domain}"
    source = _open_directory(warehouse, ref, cwd, CONTEXTS_DIR)
    (record,) = _read_named_files(source, [(name, f"{CONTEXTS_DIR}{name}.md")])
    return ProfileResult(
        warehouse=str(source.warehouse),
        ref=ref,
        sha=source.sha,
        domain=domain,
        profile=record,
        warnings=_warnings([record]),
    )


def read_agents(
    warehouse: Path | None, ref: str, cwd: Path, names: list[str]
) -> AgentsResult:
    """Read the agent definitions ``names`` at ``ref``, in the order given."""
    unique = list(dict.fromkeys(check_agent_name(name) for name in names))
    source = _open_directory(warehouse, ref, cwd, AGENTS_DIR)
    items = [(name, f"{AGENTS_DIR}{name}.md") for name in unique]
    records = _read_named_files(source, items)
    return AgentsResult(
        warehouse=str(source.warehouse),
        ref=ref,
        sha=source.sha,
        agents=records,
        warnings=_warnings(records),
    )


def decision_rules_section(text: str) -> str | None:
    """Return the body of the first ``## Decision rules`` section, or None.

    The body runs from the line after the heading to the next line that starts
    with ``## `` or equals ``---``, or to the end of the text. Leading and trailing
    blank lines are dropped. Lines are joined with ``\\n``, with no trailing newline.
    """
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(_DECISION_RULES_HEADING)),
        None,
    )
    if start is None:
        return None

    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## ") or line == "---":
            break
        body.append(line)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body)


def read_decision_rules(
    warehouse: Path | None, ref: str, cwd: Path
) -> DecisionRulesResult:
    """Return the decision-rules section of every context that has one."""
    source = _open_directory(warehouse, ref, cwd, CONTEXTS_DIR)
    rules: list[DecisionRule] = []
    for path in sorted(p for p in source.listing if is_context_path(p)):
        section = decision_rules_section(_decode_blob(source, path))
        if section is None:
            continue
        name = path.removeprefix(CONTEXTS_DIR).removesuffix(".md")
        rules.append(DecisionRule(name=name, path=path, body=section))
    return DecisionRulesResult(
        warehouse=str(source.warehouse), ref=ref, sha=source.sha, rules=rules
    )
