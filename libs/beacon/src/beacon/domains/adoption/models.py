"""Data models for artifact adoption."""

from __future__ import annotations

from dataclasses import dataclass, field

ADOPTABLE_TYPES = ("contexts", "skills", "agents")
NEW_TAG_MAX_COMMITS = 5  # only show "[added N commits ago]" if within this many commits


@dataclass
class AdoptCandidate:
    """A warehouse artifact in the warehouse-vs-beacon.yaml diff."""

    artifact_type: str  # "contexts" | "skills" | "agents"
    path: str  # warehouse-relative path (e.g. "contexts/foo.md", "skills/bar/")
    description: str = ""
    commits_ago: int | None = None  # set when added within NEW_TAG_MAX_COMMITS commits


@dataclass
class AdoptResult:
    """Result returned by AdoptApp.run().

    The two flows are tracked separately:
    - Warehouse browser: to_adopt / to_unadopt against beacon.yaml.
    - Pending TODO: pending_accept (adopt + remove from pending.yaml) /
      pending_reject (remove from pending.yaml only). Pending entries left
      unmarked stay in pending.yaml (deferred).
    """

    to_adopt: list[str] = field(default_factory=list)
    to_unadopt: list[str] = field(default_factory=list)
    pending_accept: list[str] = field(default_factory=list)
    pending_reject: list[str] = field(default_factory=list)
