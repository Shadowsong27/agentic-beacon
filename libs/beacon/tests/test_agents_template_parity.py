"""Test that examples/sample-warehouse/agents/README.md matches the template (Phase 11, task 11.1).

TDD Test Cases (11.1):
- TC1: Both files exist, content identical → passes
- TC2: Content differs → fails with informative message
"""

from pathlib import Path


def _repo_root() -> Path:
    """Return the repository root (agentic-beacon/).

    File is at: libs/beacon/tests/test_agents_template_parity.py
    Parent chain: tests/ → beacon/ → libs/ → agentic-beacon/
    """
    return Path(__file__).parent.parent.parent.parent


def test_tc1_agents_readme_matches_template():
    """TC1: examples/sample-warehouse/agents/README.md must match data/templates/agents/README.md."""
    repo = _repo_root()
    template = (
        repo
        / "libs"
        / "beacon"
        / "src"
        / "beacon"
        / "data"
        / "templates"
        / "agents"
        / "README.md"
    )
    example = repo / "examples" / "sample-warehouse" / "agents" / "README.md"

    assert template.exists(), f"Template file missing: {template}"
    assert example.exists(), f"Example file missing: {example}"

    template_content = template.read_text(encoding="utf-8")
    example_content = example.read_text(encoding="utf-8")

    assert template_content == example_content, (
        "examples/sample-warehouse/agents/README.md is out of sync with the template.\n"
        "Run: cp libs/beacon/src/beacon/data/templates/agents/README.md examples/sample-warehouse/agents/README.md"
    )
