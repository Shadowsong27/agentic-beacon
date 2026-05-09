"""End-to-end integration tests for `abc adopt` with project-scoped agents.

These tests cover the CLI ↔ TUI ↔ apply-flow integration that the per-task
unit tests bypass:

- The 4.5 unit tests called `apply_adoption()` directly with agent
  selections; the CLI handler in `cli/adoption.py` had bugs that filtered
  agents OUT before reaching `apply_adoption()`.
- The 5.8 headless tests constructed `AdoptInnerApp` with an explicit
  `warehouse_path`; the CLI handler dropped that kwarg, so the real TUI's
  auto-tick state machine had no `agents.yaml` to read and silently no-oped.
- The 4.4 unit test asserted `cleanup_unadopted_artifacts()` does not remove
  global symlinks; the CLI bypassed that helper for agents and called
  `uninstall_agent_global()` directly, violating Decision 7.
- The 4.3 unit test verified `is_adopted()` checks `artifacts.agents`; both
  `discover_all()` and the CLI pre-tick used `is_agent_installed()` (global
  state) instead, breaking the post-upgrade migration path described in
  design.md Decision 4.

The tests in this module exercise the actual CLI entrypoint via Click's
CliRunner against a fixture warehouse. The TUI's `AdoptApp.run()` is
monkeypatched to return a deterministic `AdoptResult` so we can drive
adopt/unadopt scenarios without a real terminal.
"""

import yaml
from beacon.cli.main import main
from beacon.domains.adoption.models import AdoptResult
from beacon.domains.adoption.tui import AdoptApp
from click.testing import CliRunner


def _agent_warehouse(valid_warehouse):
    """Extend the shared valid_warehouse fixture with an agent + skill demo.

    Adds:
      - skills/code-review/SKILL.md
      - agents/code-reviewer.md (declared agent)
      - agents/agents.yaml mapping code-reviewer → code-review skill
    """
    skill_dir = valid_warehouse / "skills" / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: code-review\ndescription: Review code\n---\n# Code Review\n"
    )

    (valid_warehouse / "agents" / "code-reviewer.md").write_text(
        "---\nname: code-reviewer\ndescription: Reviews code\n---\n# Code Reviewer\n"
    )
    (valid_warehouse / "agents" / "agents.yaml").write_text(
        yaml.safe_dump({"code-reviewer": {"skills": ["code-review"]}})
    )
    return valid_warehouse


def _connected_project(valid_warehouse, temp_dir, monkeypatch):
    """Create a project, connect it to the warehouse, run setup."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    runner = CliRunner()
    r = runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(main, ["setup"])
    assert r.exit_code == 0, r.output
    return project_dir, runner


def _force_interactive(monkeypatch):
    """Make the CLI take the interactive (TUI) path."""
    monkeypatch.setattr("beacon.cli.adoption.is_interactive", lambda: True)


def _stub_adopt_app(monkeypatch, *, to_adopt=None, to_unadopt=None):
    """Replace AdoptApp.run() with a deterministic stub.

    Returns the captured init dict so tests can inspect how the CLI
    constructed the app (warehouse_path threading, pre-tick state, etc.).
    """
    captured: dict = {}

    real_init = AdoptApp.__init__

    def fake_init(self, candidates, pending_entries, adopted_paths, **kwargs):
        captured["candidates"] = list(candidates)
        captured["pending_entries"] = list(pending_entries)
        captured["adopted_paths"] = list(adopted_paths)
        captured["kwargs"] = dict(kwargs)
        real_init(self, candidates, pending_entries, adopted_paths, **kwargs)

    def fake_run(self):
        return AdoptResult(to_adopt=to_adopt or [], to_unadopt=to_unadopt or [])

    monkeypatch.setattr(AdoptApp, "__init__", fake_init)
    monkeypatch.setattr(AdoptApp, "run", fake_run)
    return captured


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_adopt_records_agent_in_beacon_yaml_and_wires_project_local(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """PER-113: adopting an agent updates beacon.yaml AND wires a project-local symlink.

    Agents are now project-scoped. adopt wires into .claude/agents/ (and/or
    .opencode/agents/) inside the project root — not into global tool dirs.
    """
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    # Create .claude/ so detect_agents() returns 'claudecode'
    (project_dir / ".claude").mkdir(exist_ok=True)

    _force_interactive(monkeypatch)
    _stub_adopt_app(monkeypatch, to_adopt=["agents/code-reviewer.md"])

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    # beacon.yaml updated
    beacon = yaml.safe_load(
        (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()
    )
    assert beacon["artifacts"]["agents"] == ["agents/code-reviewer.md"]

    # Project-local .claude/agents/ symlink wired
    claude_link = project_dir / ".claude" / "agents" / "code-reviewer.md"
    assert claude_link.is_symlink(), (
        f"Expected project-local .claude/agents/code-reviewer.md symlink, got nothing. "
        f"adopt output: {r.output}"
    )

    # Global dirs must NOT receive new symlinks
    for d in [
        isolated_home / ".config" / "opencode" / "agents",
        isolated_home / ".claude" / "agents",
    ]:
        if d.exists():
            assert not any(f.suffix == ".md" for f in d.rglob("*")), (
                f"Unexpected agent files in global dir {d}"
            )


def test_unadopt_agent_removes_from_beacon_yaml_and_unwires_project_local(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """PER-113: unadopting removes from beacon.yaml AND removes project-local symlinks.

    Agents are now project-scoped. Unadopt removes the project-local .claude/agents/
    and .opencode/agents/ symlinks (no longer Decision 7 — global keep is abolished).
    """
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    # Create .claude/ so detect_agents() returns 'claudecode'
    (project_dir / ".claude").mkdir(exist_ok=True)

    # Seed: agent already declared in beacon.yaml
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts: []\n  skills: []\n"
        "  agents:\n    - agents/code-reviewer.md\n"
    )

    # Plant project-local symlinks that adopt previously created
    claude_agents_dir = project_dir / ".claude" / "agents"
    claude_agents_dir.mkdir(parents=True, exist_ok=True)
    artifact_target = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "code-reviewer.md"
    )
    artifact_target.parent.mkdir(parents=True, exist_ok=True)
    artifact_target.symlink_to(wh / "agents" / "code-reviewer.md")
    claudecode_link = claude_agents_dir / "code-reviewer.md"
    claudecode_link.symlink_to(artifact_target)

    _force_interactive(monkeypatch)
    _stub_adopt_app(monkeypatch, to_unadopt=["agents/code-reviewer.md"])

    # Pass "y\n" to confirm the artifact symlink removal prompt
    r = runner.invoke(main, ["adopt"], input="y\n")
    assert r.exit_code == 0, r.output

    # beacon.yaml: agent removed
    beacon = yaml.safe_load(beacon_yaml.read_text())
    assert beacon["artifacts"]["agents"] == []

    # Project-local symlink must be removed
    assert not claudecode_link.exists(), (
        "Expected .claude/agents/code-reviewer.md to be removed after unadopt"
    )


def test_pre_tick_state_reflects_beacon_yaml_not_global_install(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """Per Decision 1: the TUI represents project intent.

    A globally-installed agent that this project has NOT declared must NOT
    show as adopted in the TUI's pre-tick state. Otherwise multi-project
    machines bleed agent state across project boundaries.
    """
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    # Globally installed by some OTHER project — but not in this beacon.yaml
    (isolated_home / ".config" / "opencode").mkdir(parents=True, exist_ok=True)
    link = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(wh / "agents" / "code-reviewer.md")

    _force_interactive(monkeypatch)
    captured = _stub_adopt_app(monkeypatch)

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    # The agent must NOT appear in adopted_paths (project state is empty)
    assert "agents/code-reviewer.md" not in captured["adopted_paths"]


def test_globally_installed_agent_appears_as_adoption_candidate_post_upgrade(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """Migration path (design.md Decision 4): existing globally-installed agents
    must appear as candidates so the user can opt them into per-project tracking.

    Pre-fix bug: discover_all filtered with is_agent_installed → globally
    installed agents were filtered OUT → users could not see them in the TUI
    to declare them per-project, breaking the documented migration.
    """
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    # Simulate "existing user upgrades Beacon": agent globally installed,
    # not in beacon.yaml.artifacts.agents
    (isolated_home / ".config" / "opencode").mkdir(parents=True, exist_ok=True)
    link = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(wh / "agents" / "code-reviewer.md")

    _force_interactive(monkeypatch)
    captured = _stub_adopt_app(monkeypatch)

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    candidate_paths = [c.path for c in captured["candidates"]]
    assert "agents/code-reviewer.md" in candidate_paths


def test_adopt_app_is_constructed_with_warehouse_path_kwarg(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """The TUI's auto-tick state machine needs warehouse_path to read agents.yaml.

    Pre-fix bug: cli/adoption.py constructed AdoptApp with warehouse_name
    only (just the basename string for display), leaving warehouse_path at
    its None default. AdoptInnerApp._load_agent_skills() short-circuited to
    [] when warehouse_path was None → the auto-tick logic silently no-oped
    in the real TUI even though the 5.8 headless tests passed.
    """
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    _force_interactive(monkeypatch)
    captured = _stub_adopt_app(monkeypatch)

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    assert captured["kwargs"].get("warehouse_path") is not None, (
        "AdoptApp must receive warehouse_path so the inner app can load "
        "agents.yaml for the auto-tick state machine."
    )
    assert captured["kwargs"]["warehouse_path"].resolve() == wh.resolve()


def test_adopt_mixed_agent_and_skill_records_both_in_beacon_yaml(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """Adopting an agent + its required skill in one TUI confirm round-trips
    through apply_adoption — both end up in beacon.yaml in the right slots."""
    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    (isolated_home / ".config" / "opencode").mkdir(parents=True, exist_ok=True)

    _force_interactive(monkeypatch)
    _stub_adopt_app(
        monkeypatch,
        to_adopt=["agents/code-reviewer.md", "skills/code-review/"],
    )

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    beacon = yaml.safe_load(
        (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()
    )
    assert beacon["artifacts"]["agents"] == ["agents/code-reviewer.md"]
    assert beacon["artifacts"]["skills"] == ["skills/code-review/"]


def test_adopt_agent_with_no_tool_dirs_prints_wiring_note(
    valid_warehouse, temp_dir, monkeypatch, isolated_home
):
    """PER-121: when an agent is accepted but no .claude/ or .opencode/ dirs exist,
    the adopt output must include a wiring note explaining the skip and remediation."""
    import shutil

    wh = _agent_warehouse(valid_warehouse)
    project_dir, runner = _connected_project(wh, temp_dir, monkeypatch)

    # Ensure no tool directories exist
    for tool_dir in [project_dir / ".claude", project_dir / ".opencode"]:
        if tool_dir.exists():
            shutil.rmtree(tool_dir)

    _force_interactive(monkeypatch)
    _stub_adopt_app(monkeypatch, to_adopt=["agents/code-reviewer.md"])

    r = runner.invoke(main, ["adopt"])
    assert r.exit_code == 0, r.output

    # beacon.yaml updated with agent
    beacon = yaml.safe_load(
        (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()
    )
    assert beacon["artifacts"]["agents"] == ["agents/code-reviewer.md"]

    # No tool symlinks created
    assert not (project_dir / ".claude" / "agents" / "code-reviewer.md").exists()
    assert not (project_dir / ".opencode" / "agents" / "code-reviewer.md").exists()

    # Wiring note must explain the skip and the remediation
    assert "no tool directories found" in r.output, (
        f"Expected wiring note in adopt output; got:\n{r.output}"
    )
    assert "mkdir .claude" in r.output, (
        f"Expected remediation hint in adopt output; got:\n{r.output}"
    )
