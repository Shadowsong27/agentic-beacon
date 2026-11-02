"""Index the contexts of a warehouse commit as data (abc context index).

Reads committed git objects only. The working tree is never consulted, so the
output for a given ref does not change with uncommitted edits.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from beacon.core.dependencies.frontmatter import parse_frontmatter_text
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.warehouse.warehouse_path import (
    WarehousePathMissing,
    WarehousePathNotARepo,
    WarehousePathOK,
    validate_warehouse_path,
)
from beacon.utils.git import list_tree_paths, read_blob, resolve_commit

DESCRIPTION_KEY = "description"
CONTEXTS_PREFIX = "contexts/"


class ContextIndexError(Exception):
    """A context index cannot be built. The message names the cause."""


@dataclass
class ContextEntry:
    """One context listed in the index."""

    name: str
    path: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "path": self.path, "description": self.description}


@dataclass
class ContextIndex:
    """The index of one warehouse commit. Warnings are not part of the JSON."""

    warehouse: str
    ref: str
    sha: str
    contexts: list[ContextEntry]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "warehouse": self.warehouse,
            "ref": self.ref,
            "sha": self.sha,
            "contexts": [entry.to_dict() for entry in self.contexts],
        }


def describe_context(path: str, text: str | None) -> tuple[ContextEntry, str | None]:
    """Describe one context from its path and its decoded text.

    ``text`` is None when the blob is not valid UTF-8. Returns the entry and a
    warning string (``"<path>: <reason>"``) when the description is unusable.
    The entry is always returned, with ``description`` set to ``""`` in that case.
    """
    name = path.removeprefix(CONTEXTS_PREFIX).removesuffix(".md")
    entry = ContextEntry(name=name, path=path, description="")

    if text is None:
        return entry, f"{path}: file is not valid UTF-8"

    parsed = parse_frontmatter_text(text)
    if not parsed.success or parsed.data is None:
        return entry, f"{path}: {parsed.message}"

    if DESCRIPTION_KEY not in parsed.data:
        return entry, f"{path}: frontmatter has no '{DESCRIPTION_KEY}' key"

    value = parsed.data[DESCRIPTION_KEY]
    if not isinstance(value, str):
        return entry, f"{path}: '{DESCRIPTION_KEY}' is not a string"

    stripped = value.strip()
    if not stripped:
        return entry, f"{path}: '{DESCRIPTION_KEY}' is empty"

    entry.description = stripped
    return entry, None


def resolve_index_warehouse(warehouse: Path | None, cwd: Path) -> Path:
    """Return the git root of the warehouse to index.

    Uses ``warehouse`` when given. Otherwise uses the warehouse connected in
    ``<cwd>/.agentic-beacon/config.toml``. Raises ContextIndexError when neither
    applies or the path is not a usable git working tree.
    """
    if warehouse is not None:
        raw = warehouse
    else:
        config_path = cwd / ".agentic-beacon" / "config.toml"
        if not config_path.exists():
            raise ContextIndexError(
                "no warehouse given and none connected "
                "(pass --warehouse PATH or run 'abc warehouse connect')"
            )
        try:
            raw = Path(WorkspaceConfig().warehouse.local_path)
        except (ValidationError, OSError, tomllib.TOMLDecodeError) as exc:
            raise ContextIndexError(
                f"cannot read warehouse connection from {config_path}: {exc}"
            ) from exc

    result = validate_warehouse_path(raw)
    if isinstance(result, WarehousePathMissing):
        raise ContextIndexError(f"warehouse path does not exist: {result.path}")
    if isinstance(result, WarehousePathNotARepo):
        raise ContextIndexError(
            f"warehouse path is not a git repository: {result.path} ({result.reason})"
        )
    assert isinstance(result, WarehousePathOK)
    return result.path


def build_context_index(warehouse: Path, ref: str) -> ContextIndex:
    """Index the contexts at ``ref`` in the git repository ``warehouse``."""
    sha = resolve_commit(warehouse, ref)
    if sha is None:
        raise ContextIndexError(f"ref '{ref}' not found in warehouse {warehouse}")

    paths = list_tree_paths(warehouse, sha, CONTEXTS_PREFIX)
    if paths is None:
        raise ContextIndexError(
            f"git ls-tree failed for {sha} in warehouse {warehouse}"
        )
    if not paths:
        raise ContextIndexError(
            f"no contexts/ directory at {sha} in warehouse {warehouse}"
        )

    context_paths = sorted(p for p in paths if _is_context_path(p))

    entries: list[ContextEntry] = []
    warnings: list[str] = []
    for path in context_paths:
        blob = read_blob(warehouse, sha, path)
        if blob is None:
            raise ContextIndexError(
                f"git show failed for {path} at {sha} in warehouse {warehouse}"
            )
        try:
            text: str | None = blob.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        entry, warning = describe_context(path, text)
        entries.append(entry)
        if warning is not None:
            warnings.append(warning)

    return ContextIndex(
        warehouse=str(warehouse),
        ref=ref,
        sha=sha,
        contexts=entries,
        warnings=warnings,
    )


def index_contexts(warehouse: Path | None, ref: str, cwd: Path) -> ContextIndex:
    """Resolve the warehouse, then index the contexts at ``ref``."""
    resolved = resolve_index_warehouse(warehouse, cwd)
    return build_context_index(resolved, ref)


def _is_context_path(path: str) -> bool:
    """True for a ``.md`` file that is neither a dot-file nor a README."""
    basename = path.rsplit("/", 1)[-1]
    return (
        basename.endswith(".md")
        and not basename.startswith(".")
        and basename.lower() != "readme.md"
    )
