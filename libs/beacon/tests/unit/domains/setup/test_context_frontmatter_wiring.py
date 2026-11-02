"""Context frontmatter must not change what `abc sync` wires (AB-109 D7).

Wiring writes only context paths. A context with a `description` frontmatter
block and one without must produce the same CLAUDE.md @-lines and the same
opencode.json instructions as a run without frontmatter.
"""

from __future__ import annotations

import json
from pathlib import Path

from beacon.domains.setup.wiring import wire_contexts_claudecode, wire_contexts_opencode

DESCRIBED_BODY = "# Described\n"
DESCRIBED_WITH_FRONTMATTER = (
    "---\ndescription: Load when working on CI.\n---\n" + DESCRIBED_BODY
)


def _wire_project(root: Path, described_content: str) -> tuple[str, dict]:
    """Build a project under `root` with two contexts and wire it.

    Returns the CLAUDE.md text and the opencode.json instructions list.
    """
    project = root / "project"
    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    contexts = artifacts_dir / "contexts"
    contexts.mkdir(parents=True)
    (contexts / "described.md").write_text(described_content)
    (contexts / "plain.md").write_text("# Plain\n")
    (project / "CLAUDE.md").write_text("# Project\n")
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))

    wire_contexts_claudecode(project, artifacts_dir)
    wire_contexts_opencode(project, artifacts_dir)

    claude_md = (project / "CLAUDE.md").read_text()
    opencode = json.loads((project / "opencode.json").read_text())
    return claude_md, opencode


def test_frontmatter_does_not_change_claude_or_opencode_wiring(tmp_path):
    """TC1-TC3: wiring lists exactly the two context paths, identical with or without frontmatter."""
    expected_paths = [
        ".agentic-beacon/artifacts/contexts/described.md",
        ".agentic-beacon/artifacts/contexts/plain.md",
    ]

    with_fm_md, with_fm_json = _wire_project(
        tmp_path / "with", DESCRIBED_WITH_FRONTMATTER
    )
    without_fm_md, without_fm_json = _wire_project(
        tmp_path / "without", DESCRIBED_BODY
    )

    at_lines = [line for line in with_fm_md.splitlines() if line.startswith("@")]
    assert at_lines == [f"@{path}" for path in expected_paths]
    assert with_fm_json["instructions"] == expected_paths
    assert with_fm_md == without_fm_md
    assert with_fm_json == without_fm_json
