"""Pending artifact manifest models for Agentic Beacon.

Defines the structure of .agentic-beacon/pending.yaml — a per-project,
gitignored file that buffers artifacts authored in the warehouse but not yet
wired into beacon.yaml via `abc adopt`.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from beacon.core.exceptions import ValidationError, YAMLParseError


class PendingEntry(BaseModel):
    """A single pending artifact entry."""

    path: str
    type: Literal["knowledge", "skill", "context", "agent"]
    action: Literal["created", "modified"]
    source: str
    created_at: datetime


class PendingManifest(BaseModel):
    """Parsed representation of .agentic-beacon/pending.yaml."""

    pending: list[PendingEntry] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "PendingManifest":
        """Load pending manifest from YAML file.

        Tolerates absent file (returns empty manifest).
        Raises ValidationError on schema violations.
        """
        if not path.exists():
            return cls(pending=[])

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise YAMLParseError(f"Invalid YAML in {path}: {e}") from e

        if data is None:
            return cls(pending=[])

        if not isinstance(data, dict):
            raise ValidationError(
                f"pending.yaml must be a YAML mapping, got {type(data).__name__}"
            )

        raw_entries = data.get("pending", [])
        if raw_entries is None:
            return cls(pending=[])

        if not isinstance(raw_entries, list):
            raise ValidationError("'pending' field must be a list")

        entries: list[PendingEntry] = []
        for i, raw in enumerate(raw_entries):
            try:
                entries.append(PendingEntry.model_validate(raw))
            except PydanticValidationError as e:
                first_err = e.errors()[0]
                field = ".".join(str(loc) for loc in first_err["loc"])
                msg = first_err["msg"]
                raise ValidationError(
                    f"Invalid pending.yaml entry at index {i}: field '{field}' — {msg}"
                ) from e

        return cls(pending=entries)

    def to_yaml(self, path: Path) -> None:
        """Write pending manifest to YAML file.

        Field order preserved: path / type / action / source / created_at.
        Trailing newline guaranteed.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        serialized_entries = []
        for entry in self.pending:
            dt = entry.created_at
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            created_at_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            serialized_entries.append(
                {
                    "path": entry.path,
                    "type": entry.type,
                    "action": entry.action,
                    "source": entry.source,
                    "created_at": created_at_str,
                }
            )

        data = {"pending": serialized_entries}

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def append(self, entry: PendingEntry) -> None:
        """Append entry to the in-memory list. Persist via to_yaml."""
        self.pending.append(entry)
