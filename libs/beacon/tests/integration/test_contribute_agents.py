"""Tests for abc contribute agent definition support.

Agents (~/.config/opencode/agents/, ~/.claude/agents/) are now included in
the contribute scope automatically — no beacon.yaml entry required.

Test Cases:
- TC1: contribute <agents/file> — single modified agent contributed to warehouse
- TC2: contribute (all) — modified agent included alongside other artifacts
- TC3: contribute --dry-run — modified agent shown in preview, warehouse unchanged
- TC4: contribute <agents/file> — agent identical to warehouse → nothing to contribute
- TC5: contribute <agents/file> — agent not in warehouse (new file) → added
- TC6: Two tools have identical modified copies → one copy contributed (no prompt)
- TC7: Cold start — agent exists in global dir, no warehouse counterpart at all → added
"""

from pathlib import Path

import pytest
from beacon.cli.main import main
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def warehouse(tmp_path):
    """Warehouse with an agent definition and a knowledge file."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nOriginal.\n")
    (wh / "agents" / "reviewer.md").write_text("# Reviewer\nWarehouse version.\n")
    return wh


@pytest.fixture
def project(tmp_path, warehouse, fake_home, monkeypatch):
    """Connected project with a synced knowledge artifact."""
    proj = tmp_path / "project"
    proj.mkdir()
    monkeypatch.chdir(proj)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])
    beacon_yaml = proj / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )
    runner.invoke(main, ["sync", "--skip-git-check"])
    return proj, warehouse, runner


# ---------------------------------------------------------------------------
# TC1: contribute single modified agent
# ---------------------------------------------------------------------------


def test_contribute_single_modified_agent(project, fake_home):
    """TC1: abc contribute agents/reviewer.md — modified global copy → warehouse updated."""
    proj, warehouse, runner = project

    # Globally modified agent
    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "reviewer.md").write_text("# Reviewer\nImproved version.\n")

    result = runner.invoke(
        main,
        ["contribute", "agents/reviewer.md", "--skip-git-check"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "Improved version." in (warehouse / "agents" / "reviewer.md").read_text()


# ---------------------------------------------------------------------------
# TC2: contribute all — modified agent included automatically
# ---------------------------------------------------------------------------


def test_contribute_all_includes_modified_agent(project, fake_home):
    """TC2: abc contribute (all) — modified agent is included without beacon.yaml entry."""
    proj, warehouse, runner = project

    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "reviewer.md").write_text("# Reviewer\nImproved version.\n")

    result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "Improved version." in (warehouse / "agents" / "reviewer.md").read_text()


# ---------------------------------------------------------------------------
# TC3: dry-run — warehouse unchanged, preview shown
# ---------------------------------------------------------------------------


def test_contribute_agent_dry_run(project, fake_home):
    """TC3: --dry-run shows the agent in preview but does not write to warehouse."""
    proj, warehouse, runner = project

    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "reviewer.md").write_text("# Reviewer\nImproved version.\n")

    result = runner.invoke(
        main, ["contribute", "agents/reviewer.md", "--dry-run", "--skip-git-check"]
    )

    assert result.exit_code == 0, result.output
    assert "agents/reviewer.md" in result.output
    # Warehouse must be unchanged
    assert "Warehouse version." in (warehouse / "agents" / "reviewer.md").read_text()


# ---------------------------------------------------------------------------
# TC4: agent identical to warehouse → nothing to contribute
# ---------------------------------------------------------------------------


def test_contribute_agent_identical_is_noop(project, fake_home):
    """TC4: Global agent identical to warehouse → nothing to contribute."""
    proj, warehouse, runner = project

    # Install identical copy globally
    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "reviewer.md").write_text("# Reviewer\nWarehouse version.\n")

    result = runner.invoke(
        main,
        ["contribute", "agents/reviewer.md", "--skip-git-check"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "nothing" in result.output.lower()
    # Warehouse unchanged
    assert "Warehouse version." in (warehouse / "agents" / "reviewer.md").read_text()


# ---------------------------------------------------------------------------
# TC5: agent not yet in warehouse → added
# ---------------------------------------------------------------------------


def test_contribute_new_agent_added_to_warehouse(project, fake_home):
    """TC5: Global agent file has no warehouse counterpart → added as new file."""
    proj, warehouse, runner = project

    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "new-agent.md").write_text("# New Agent\nBrand new.\n")
    # Add to warehouse agents dir so comparator finds it
    (warehouse / "agents" / "new-agent.md").write_text("# New Agent\nOld.\n")

    result = runner.invoke(
        main,
        ["contribute", "agents/new-agent.md", "--skip-git-check"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "Brand new." in (warehouse / "agents" / "new-agent.md").read_text()


# ---------------------------------------------------------------------------
# TC6: Two tools with identical modified copies → no prompt, one copy used
# ---------------------------------------------------------------------------


def test_contribute_agent_two_identical_tools_no_prompt(project, fake_home):
    """TC6: Both opencode and claudecode have the same modified copy → no conflict prompt."""
    proj, warehouse, runner = project

    content = "# Reviewer\nSame improvement everywhere.\n"

    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "reviewer.md").write_text(content)

    cc_agents = fake_home / ".claude" / "agents"
    cc_agents.mkdir(parents=True, exist_ok=True)
    (cc_agents / "reviewer.md").write_text(content)

    # input only has the confirm "y" — no conflict choice prompt expected
    result = runner.invoke(
        main,
        ["contribute", "agents/reviewer.md", "--skip-git-check"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (
        "Same improvement everywhere."
        in (warehouse / "agents" / "reviewer.md").read_text()
    )


# ---------------------------------------------------------------------------
# TC7: Cold start — agent exists only in global dir (no warehouse counterpart)
# ---------------------------------------------------------------------------


def test_contribute_cold_start_agent_no_warehouse_counterpart(project, fake_home):
    """TC7: Agent exists in global dir but has NO warehouse counterpart.

    This is the 'cold start' scenario: a user has agents installed globally that
    have never been contributed to the warehouse. The contribute command must
    copy the file rather than skipping with 'no modified copy found'.
    """
    proj, warehouse, runner = project

    oc_agents = fake_home / ".config" / "opencode" / "agents"
    oc_agents.mkdir(parents=True, exist_ok=True)
    (oc_agents / "brand-new-agent.md").write_text("# Brand New Agent\nFirst version.\n")

    # Confirm no warehouse counterpart exists before contributing
    assert not (warehouse / "agents" / "brand-new-agent.md").exists()

    result = runner.invoke(
        main,
        ["contribute", "--skip-git-check"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (warehouse / "agents" / "brand-new-agent.md").exists()
    assert "First version." in (warehouse / "agents" / "brand-new-agent.md").read_text()
