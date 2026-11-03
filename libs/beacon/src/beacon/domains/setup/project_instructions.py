"""Read a repo's AGENTS.md at a commit with beacon-owned imports removed (abc project instructions).

Reads committed git objects only. The working tree is never consulted.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from beacon.domains.setup.wiring import split_owned_imports
from beacon.domains.warehouse.warehouse_read import (
    ItemMissingError,
    WarehouseReadError,
    resolve_repo_root,
)
from beacon.utils.git import list_tree_paths, read_blob, resolve_commit

INSTRUCTIONS_PATH = "AGENTS.md"


@dataclass
class ProjectInstructions:
    repo: str
    ref: str
    sha: str
    text: str
    removed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "ref": self.ref,
            "sha": self.sha,
            "path": INSTRUCTIONS_PATH,
            "text": self.text,
            "removed": self.removed,
        }


def _tidy(text: str) -> str:
    """Collapse 3+ newlines, drop trailing blank lines, end with one newline or be empty."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.splitlines(keepends=True)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    joined = "".join(lines)
    return joined if joined.endswith("\n") else joined + "\n"


def read_project_instructions(repo: Path, ref: str) -> ProjectInstructions:
    """Read the root AGENTS.md of ``repo`` at ``ref`` and strip beacon-owned imports."""
    root = resolve_repo_root(repo)

    sha = resolve_commit(root, ref)
    if sha is None:
        raise WarehouseReadError(f"ref '{ref}' not found in repo {root}")

    listing = list_tree_paths(root, sha, INSTRUCTIONS_PATH)
    if listing is None:
        raise WarehouseReadError(f"git ls-tree failed for {sha} in repo {root}")
    if INSTRUCTIONS_PATH not in listing:
        raise ItemMissingError(sha, [INSTRUCTIONS_PATH])

    blob = read_blob(root, sha, INSTRUCTIONS_PATH)
    if blob is None:
        raise WarehouseReadError(f"git show failed for {INSTRUCTIONS_PATH} at {sha}")
    try:
        content = blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WarehouseReadError(
            f"{INSTRUCTIONS_PATH} at {sha} is not valid UTF-8"
        ) from exc

    removed, kept = split_owned_imports(content)
    return ProjectInstructions(
        repo=str(root),
        ref=ref,
        sha=sha,
        text=_tidy("".join(kept)),
        removed=removed,
    )
