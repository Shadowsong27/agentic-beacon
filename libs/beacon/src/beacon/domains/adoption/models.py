"""Data models for artifact adoption."""

from __future__ import annotations

from dataclasses import dataclass, field

ADOPTABLE_TYPES = ("contexts", "skills", "knowledge", "agents")
NEW_TAG_MAX_COMMITS = 5  # only show "[added N commits ago]" if within this many commits
KNOWLEDGE_SUBTYPES = frozenset(("decisions", "lessons", "facts"))


@dataclass
class AdoptCandidate:
    """A warehouse artifact that can be adopted into beacon.yaml."""

    artifact_type: str  # "contexts" | "skills" | "knowledge"
    path: str  # warehouse-relative path (e.g. "contexts/foo.md", "skills/bar/")
    description: str = ""
    is_new: bool = True  # kept for backward compat; prefer commits_ago is not None
    commits_ago: int | None = None  # set when added within NEW_TAG_MAX_COMMITS commits


@dataclass
class AdoptResult:
    """Result returned by AdoptApp.run()."""

    to_adopt: list[str] = field(default_factory=list)
    to_unadopt: list[str] = field(default_factory=list)
