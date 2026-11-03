"""Integration tests for the abc read commands (AB-122) against real temporary git repos.

Covers context show / intake-policy / operate-profile / decision-rules, agent show and
project instructions through Click's CliRunner, with stdout and stderr separated.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from beacon.cli.main import main
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from click.testing import CliRunner

pytestmark = pytest.mark.integration

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}

ALPHA = "---\ndescription: Alpha.\n---\n# Alpha\n"
BETA_RULES = "---\ndescription: Beta.\n---\n# Beta\n\n## Decision rules\n\nDR2 beta\n"
RULES = "# Rules\n\n## Decision rules\n\nDR1 first.\n\n## Other\nnot a rule\n"
SELECTOR = (
    "---\nname: context-selector\ndescription: Selects.\nmode: subagent\n---\n"
    "Body here.\n"
)
BROKEN_AGENT = "---\nname: [oops\n---\nBroken body\n"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **_GIT_ENV},
    )
    return result.stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _make_repo(root: Path, commits: list[dict[str, str]]) -> tuple[Path, list[str]]:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    shas = [_commit(root, files, f"commit {i}") for i, files in enumerate(commits)]
    return root, shas


@pytest.fixture
def warehouse(tmp_path: Path) -> dict[str, object]:
    """Commit 1 has contexts only; commit 2 adds agents/. Returns both SHAs."""
    repo, (first, head) = _make_repo(
        tmp_path / "warehouse",
        [
            {
                "contexts/alpha.md": ALPHA,
                "contexts/teams/beta.md": BETA_RULES,
                "contexts/rules.md": RULES,
                "contexts/plain.md": "# Plain\n",
                "contexts/intake-policy-AB.md": "# AB intake\n",
                "contexts/operate-conductor.md": "# Conductor\n",
                "contexts/operate-airflow-platform.md": "# Airflow\n",
            },
            {
                "agents/context-selector.md": SELECTOR,
                "agents/broken.md": BROKEN_AGENT,
            },
        ],
    )
    return {"path": repo, "first_sha": first, "head_sha": head}


def _project(tmp_path: Path, agents_md: str | None = None) -> Path:
    """A project repo with one commit. AGENTS.md is committed only when given."""
    files = {"README.md": "x\n"} if agents_md is None else {"AGENTS.md": agents_md}
    repo, _ = _make_repo(tmp_path / "project", [files])
    return repo


def _run(args: list[str]) -> tuple[int, str, str]:
    result = CliRunner().invoke(main, args)
    return result.exit_code, result.stdout, result.stderr


def _status(repo: Path) -> str:
    return _git(repo, "status", "--porcelain")


def _pending_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chdir into a project with a non-empty pending.yaml, so the pending alert fires."""
    project = _project(tmp_path / "pending", AGENTS_FIXTURE)
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    entry = PendingEntry(
        path="skills/new-skill/",
        type="skill",
        action="created",
        source="record-skill",
        created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    PendingManifest(pending=[entry]).to_yaml(beacon_dir / "pending.yaml")
    monkeypatch.chdir(project)


AGENTS_FIXTURE = (
    "# Project\n\n"
    "@.agentic-beacon/artifacts/contexts/a.md\n"
    "@.agentic-beacon/artifacts/agents/b.md\n\n\n\n"
    "Rules here.\n"
    "@AGENTS.md\n"
    "@.agentic-beacon/artifacts/contexts/a.md\n\n"
)


# ---------------------------------------------------------------------------
# context show (tasks 2.2)
# ---------------------------------------------------------------------------


def test_show_returns_records_in_given_order_with_sha(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = warehouse["path"]

    code, out, err = _run(
        ["context", "show", "teams/beta", "alpha", "--warehouse", str(repo)]
    )

    assert code == 0, err
    data = json.loads(out)
    assert data["sha"] == warehouse["head_sha"]
    assert data["ref"] == "HEAD"
    assert [c["name"] for c in data["contexts"]] == ["teams/beta", "alpha"]
    assert [c["path"] for c in data["contexts"]] == [
        "contexts/teams/beta.md",
        "contexts/alpha.md",
    ]
    alpha = data["contexts"][1]
    assert alpha["text"] == ALPHA
    assert alpha["frontmatter"] == {"description": "Alpha."}
    assert alpha["body"] == "# Alpha\n"


def test_show_repeated_name_printed_once(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["context", "show", "alpha", "alpha", "--warehouse", str(warehouse["path"])]
    )

    assert code == 0, err
    assert [c["name"] for c in json.loads(out)["contexts"]] == ["alpha"]


def test_show_missing_names_exit_3_listing_all(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    head = warehouse["head_sha"]

    code, out, err = _run(
        [
            "context",
            "show",
            "alpha",
            "gone",
            "teams/nope",
            "--warehouse",
            str(warehouse["path"]),
        ]
    )

    assert code == 3
    assert out == ""
    assert err.strip() == (
        f"error: missing at {head}: contexts/gone.md, contexts/teams/nope.md"
    )


@pytest.mark.parametrize("name", ["alpha.md", "../x", "a//b"])
def test_show_bad_name_exit_2(warehouse, tmp_path, monkeypatch, name):
    monkeypatch.chdir(tmp_path)

    code, out, _ = _run(
        ["context", "show", name, "--warehouse", str(warehouse["path"])]
    )

    assert code == 2
    assert out == ""


# ---------------------------------------------------------------------------
# context intake-policy / operate-profile (tasks 2.3)
# ---------------------------------------------------------------------------


def test_intake_policy_reads_board_context(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["context", "intake-policy", "AB", "--warehouse", str(warehouse["path"])]
    )

    assert code == 0, err
    data = json.loads(out)
    assert data["board"] == "AB"
    assert data["sha"] == warehouse["head_sha"]
    assert data["policy"]["name"] == "intake-policy-AB"
    assert data["policy"]["path"] == "contexts/intake-policy-AB.md"
    assert data["policy"]["text"] == "# AB intake\n"


@pytest.mark.parametrize("board", ["ZZ", "ab"], ids=["absent", "case-sensitive"])
def test_intake_policy_missing_board_exit_3(warehouse, tmp_path, monkeypatch, board):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["context", "intake-policy", board, "--warehouse", str(warehouse["path"])]
    )

    assert code == 3
    assert out == ""
    assert f"contexts/intake-policy-{board}.md" in err


def test_operate_profile_reads_domain_context(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        [
            "context",
            "operate-profile",
            "airflow-platform",
            "--warehouse",
            str(warehouse["path"]),
        ]
    )

    assert code == 0, err
    data = json.loads(out)
    assert data["domain"] == "airflow-platform"
    assert data["profile"]["path"] == "contexts/operate-airflow-platform.md"
    assert data["profile"]["name"] == "operate-airflow-platform"


def test_operate_profile_missing_domain_exit_3(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["context", "operate-profile", "nope", "--warehouse", str(warehouse["path"])]
    )

    assert code == 3
    assert out == ""
    assert "contexts/operate-nope.md" in err


@pytest.mark.parametrize("value", ["A/B", "-x", "x.y", "../x"])
def test_board_and_domain_bad_names_exit_2(warehouse, tmp_path, monkeypatch, value):
    monkeypatch.chdir(tmp_path)
    wh = str(warehouse["path"])

    board_code, _, _ = _run(["context", "intake-policy", value, "--warehouse", wh])
    domain_code, _, _ = _run(["context", "operate-profile", value, "--warehouse", wh])

    assert board_code == 2
    assert domain_code == 2


# ---------------------------------------------------------------------------
# context decision-rules (tasks 2.5)
# ---------------------------------------------------------------------------


def test_decision_rules_lists_sections_sorted_by_path(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["context", "decision-rules", "--warehouse", str(warehouse["path"])])

    assert code == 0, err
    data = json.loads(out)
    assert data["sha"] == warehouse["head_sha"]
    assert data["rules"] == [
        {"name": "rules", "path": "contexts/rules.md", "body": "DR1 first."},
        {"name": "teams/beta", "path": "contexts/teams/beta.md", "body": "DR2 beta"},
    ]


def test_decision_rules_none_is_exit_0_with_empty_list(tmp_path, monkeypatch):
    repo, (sha,) = _make_repo(
        tmp_path / "plain", [{"contexts/plain.md": "---\ndescription: P.\n---\n"}]
    )
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["context", "decision-rules", "--warehouse", str(repo)])

    assert code == 0, err
    assert json.loads(out) == {
        "warehouse": str(repo.resolve()),
        "ref": "HEAD",
        "sha": sha,
        "rules": [],
    }


# ---------------------------------------------------------------------------
# agent show (tasks 2.4)
# ---------------------------------------------------------------------------


def test_agent_show_parses_frontmatter_and_body(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["agent", "show", "context-selector", "--warehouse", str(warehouse["path"])]
    )

    assert code == 0, err
    data = json.loads(out)
    assert data["sha"] == warehouse["head_sha"]
    (agent,) = data["agents"]
    assert agent["path"] == "agents/context-selector.md"
    assert agent["frontmatter"]["name"] == "context-selector"
    assert agent["body"] == "Body here.\n"


def test_agent_broken_frontmatter_exit_0_with_warning(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["agent", "show", "broken", "--warehouse", str(warehouse["path"])]
    )

    assert code == 0, err
    (agent,) = json.loads(out)["agents"]
    assert agent["frontmatter"] is None
    assert agent["body"] == "Broken body\n"
    warnings = [line for line in err.splitlines() if line.startswith("warning: ")]
    assert len(warnings) == 1
    assert warnings[0].startswith("warning: agents/broken.md: YAML parse error: ")


def test_agent_missing_exit_3(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        ["agent", "show", "nope", "--warehouse", str(warehouse["path"])]
    )

    assert code == 3
    assert out == ""
    assert "agents/nope.md" in err


def test_agent_show_bad_name_exit_2(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, _ = _run(
        ["agent", "show", "alpha.md", "--warehouse", str(warehouse["path"])]
    )

    assert code == 2
    assert out == ""


def test_agent_show_at_commit_without_agents_dir_exit_1(warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        [
            "agent",
            "show",
            "context-selector",
            "--warehouse",
            str(warehouse["path"]),
            "--ref",
            warehouse["first_sha"],
        ]
    )

    assert code == 1
    assert out == ""
    assert "no agents/ directory" in err


# ---------------------------------------------------------------------------
# project instructions (tasks 3.1)
# ---------------------------------------------------------------------------


def test_project_instructions_removes_owned_imports(tmp_path, monkeypatch):
    project = _project(tmp_path, AGENTS_FIXTURE)
    monkeypatch.chdir(tmp_path)
    head = _git(project, "rev-parse", "HEAD")

    code, out, err = _run(["project", "instructions", "--repo", str(project)])

    assert code == 0, err
    data = json.loads(out)
    assert data["sha"] == head
    assert data["path"] == "AGENTS.md"
    assert data["text"] == "# Project\n\nRules here.\n@AGENTS.md\n"
    assert data["removed"] == [
        ".agentic-beacon/artifacts/contexts/a.md",
        ".agentic-beacon/artifacts/agents/b.md",
        ".agentic-beacon/artifacts/contexts/a.md",
    ]


def test_project_instructions_only_imports_gives_empty_text(tmp_path, monkeypatch):
    project = _project(tmp_path, "@.agentic-beacon/artifacts/contexts/a.md\n")
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["project", "instructions", "--repo", str(project)])

    assert code == 0, err
    data = json.loads(out)
    assert data["text"] == ""
    assert len(data["removed"]) == 1


def test_project_instructions_missing_agents_md_exit_3(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["project", "instructions", "--repo", str(project)])

    assert code == 3
    assert out == ""
    assert "AGENTS.md" in err


def test_project_instructions_non_repo_exit_1(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["project", "instructions", "--repo", str(plain)])

    assert code == 1
    assert out == ""
    assert "not a git repository" in err


def test_project_instructions_reads_committed_content_only(tmp_path, monkeypatch):
    project = _project(tmp_path, "# Committed\n")
    (project / "AGENTS.md").write_text("# Uncommitted edit\n")
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["project", "instructions", "--repo", str(project)])

    assert code == 0, err
    assert json.loads(out)["text"] == "# Committed\n"


# ---------------------------------------------------------------------------
# Shared exit codes and read-only contract (tasks 5.2)
# ---------------------------------------------------------------------------

_WAREHOUSE_COMMANDS = {
    "show": ["context", "show", "alpha"],
    "intake-policy": ["context", "intake-policy", "AB"],
    "operate-profile": ["context", "operate-profile", "conductor"],
    "decision-rules": ["context", "decision-rules"],
    "agent-show": ["agent", "show", "context-selector"],
}


@pytest.mark.parametrize("command", list(_WAREHOUSE_COMMANDS))
def test_missing_warehouse_path_exit_1(command, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        [*_WAREHOUSE_COMMANDS[command], "--warehouse", str(tmp_path / "nope")]
    )

    assert code == 1
    assert out == ""
    assert "does not exist" in err


@pytest.mark.parametrize("command", list(_WAREHOUSE_COMMANDS))
def test_non_repo_warehouse_exit_1(command, tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(tmp_path)

    code, out, _ = _run([*_WAREHOUSE_COMMANDS[command], "--warehouse", str(plain)])

    assert code == 1
    assert out == ""


@pytest.mark.parametrize("command", list(_WAREHOUSE_COMMANDS))
def test_unknown_ref_exit_1(command, warehouse, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(
        [
            *_WAREHOUSE_COMMANDS[command],
            "--warehouse",
            str(warehouse["path"]),
            "--ref",
            "no-such-ref",
        ]
    )

    assert code == 1
    assert out == ""
    assert "not found" in err


@pytest.mark.parametrize("command", ["show", "intake-policy", "decision-rules"])
def test_no_contexts_dir_exit_1(tmp_path, monkeypatch, command):
    repo, _ = _make_repo(tmp_path / "agents-only", [{"agents/a.md": "x\n"}])
    monkeypatch.chdir(tmp_path)

    code, out, err = _run([*_WAREHOUSE_COMMANDS[command], "--warehouse", str(repo)])

    assert code == 1
    assert out == ""
    assert "no contexts/ directory" in err


def test_uncommitted_edit_does_not_change_output(warehouse, tmp_path, monkeypatch):
    repo = warehouse["path"]
    (repo / "contexts" / "alpha.md").write_text("DIRTY\n")
    (repo / "contexts" / "new-untracked.md").write_text("untracked\n")
    monkeypatch.chdir(tmp_path)

    code, out, err = _run(["context", "show", "alpha", "--warehouse", str(repo)])

    assert code == 0, err
    assert json.loads(out)["contexts"][0]["text"] == ALPHA


def test_commands_leave_git_status_unchanged(warehouse, tmp_path, monkeypatch):
    repo = warehouse["path"]
    (repo / "scratch.txt").write_text("dirty\n")
    project = _project(tmp_path, AGENTS_FIXTURE)
    (project / "scratch.txt").write_text("dirty\n")
    monkeypatch.chdir(tmp_path)
    before_repo, before_project = _status(repo), _status(project)

    for args in [
        *_WAREHOUSE_COMMANDS.values(),
        ["context", "decision-rules"],
    ]:
        code, _, err = _run([*args, "--warehouse", str(repo)])
        assert code == 0, err
    code, _, err = _run(["project", "instructions", "--repo", str(project)])
    assert code == 0, err

    assert _status(repo) == before_repo
    assert _status(project) == before_project


def test_stdout_is_json_with_pending_alert_present(warehouse, tmp_path, monkeypatch):
    _pending_cwd(tmp_path, monkeypatch)
    repo = str(warehouse["path"])

    for args in [
        ["context", "show", "alpha"],
        ["context", "intake-policy", "AB"],
        ["context", "operate-profile", "conductor"],
        ["context", "decision-rules"],
        ["agent", "show", "context-selector"],
    ]:
        code, out, err = _run([*args, "--warehouse", repo])
        assert code == 0, err
        assert json.loads(out)["sha"] == warehouse["head_sha"]
