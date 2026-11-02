"""Integration tests for abc context index against a real temporary git warehouse.

Runs the real CLI group through Click's CliRunner, with separate stdout and stderr.
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


@pytest.fixture
def warehouse(tmp_path: Path) -> dict[str, str | Path]:
    """Warehouse with two commits. The first commit's SHA is returned as first_sha."""
    repo = tmp_path / "warehouse"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    first_sha = _commit(
        repo,
        {
            "contexts/alpha.md": "---\ndescription: Alpha.\n---\n# Alpha\n",
            "contexts/plain.md": "# Plain, no frontmatter\n",
        },
        "first",
    )
    second_sha = _commit(
        repo,
        {
            "contexts/teams/backend.md": "---\ndescription: '  Backend.  '\ntitle: x\n---\n",
            "contexts/README.md": "# Contexts\n",
            "contexts/.hidden.md": "---\ndescription: Hidden.\n---\n",
        },
        "second",
    )
    return {"path": repo, "first_sha": first_sha, "head_sha": second_sha}


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    return project


def _run(args: list[str]) -> tuple[int, str, str]:
    result = CliRunner().invoke(main, ["context", "index", *args])
    return result.exit_code, result.stdout, result.stderr


def test_default_ref_lists_head_contexts(warehouse, tmp_path, monkeypatch):
    """Default ref is HEAD; README and dot-files are skipped; one warning per bad context.

    Also: an uncommitted working-tree edit is not shown, and stdout stays valid JSON
    while a non-empty pending.yaml exists in the working directory.
    """
    repo = warehouse["path"]
    project = _project(tmp_path)
    (repo / "contexts" / "alpha.md").write_text("---\ndescription: Dirty.\n---\n")
    project_pending = project / ".agentic-beacon"
    project_pending.mkdir()
    entry = PendingEntry(
        path="skills/new-skill/",
        type="skill",
        action="created",
        source="record-skill",
        created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    PendingManifest(pending=[entry]).to_yaml(project_pending / "pending.yaml")
    monkeypatch.chdir(project)

    code, out, err = _run(["--warehouse", str(repo)])

    assert code == 0, err
    data = json.loads(out)
    assert data["ref"] == "HEAD"
    assert data["sha"] == warehouse["head_sha"]
    assert data["warehouse"] == str(repo.resolve())
    assert [c["path"] for c in data["contexts"]] == [
        "contexts/alpha.md",
        "contexts/plain.md",
        "contexts/teams/backend.md",
    ]
    assert [c["name"] for c in data["contexts"]] == ["alpha", "plain", "teams/backend"]
    assert [c["description"] for c in data["contexts"]] == ["Alpha.", "", "Backend."]
    assert [line for line in err.splitlines() if line.startswith("warning: ")] == [
        "warning: contexts/plain.md: File has no YAML frontmatter (must start with ---)"
    ]


def test_ref_selects_earlier_commit(warehouse, tmp_path, monkeypatch):
    """--ref of the first commit lists only the contexts present at that commit."""
    monkeypatch.chdir(_project(tmp_path))

    code, out, err = _run(
        ["--warehouse", str(warehouse["path"]), "--ref", warehouse["first_sha"]]
    )

    assert code == 0, err
    data = json.loads(out)
    assert data["sha"] == warehouse["first_sha"]
    assert data["ref"] == warehouse["first_sha"]
    assert [c["path"] for c in data["contexts"]] == [
        "contexts/alpha.md",
        "contexts/plain.md",
    ]


def test_connected_warehouse_is_default(warehouse, tmp_path, monkeypatch):
    """Without --warehouse, the warehouse in .agentic-beacon/config.toml is indexed."""
    project = _project(tmp_path)
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse["path"]}"\n'
    )
    monkeypatch.chdir(project)

    code, out, err = _run([])

    assert code == 0, err
    assert json.loads(out)["warehouse"] == str(Path(warehouse["path"]).resolve())


@pytest.mark.parametrize(
    ("args_template", "expected"),
    [
        pytest.param(
            ["--warehouse", "{wh}", "--ref", "does-not-exist"],
            "error: ref 'does-not-exist' not found in warehouse",
            id="unknown-ref",
        ),
        pytest.param(
            ["--warehouse", "/nonexistent/warehouse"],
            "error: warehouse path does not exist: /nonexistent/warehouse",
            id="missing-path",
        ),
        pytest.param(
            ["--warehouse", "{plain}"],
            "error: warehouse path is not a git repository:",
            id="not-a-repo",
        ),
        pytest.param(
            [],
            "error: no warehouse given and none connected",
            id="nothing-connected",
        ),
    ],
)
def test_error_exits_1_with_empty_stdout(
    warehouse, tmp_path, monkeypatch, args_template, expected
):
    """Each unusable-warehouse case exits 1 with stdout empty and one error line."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(_project(tmp_path))
    args = [a.format(wh=warehouse["path"], plain=plain) for a in args_template]

    code, out, err = _run(args)

    assert code == 1
    assert out == ""
    assert any(line.startswith(expected) for line in err.splitlines()), err


def test_commit_without_contexts_directory_exits_1(tmp_path, monkeypatch):
    """A commit with no contexts/ directory is an error, not an empty index."""
    repo = tmp_path / "warehouse"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    sha = _commit(repo, {"README.md": "# Warehouse\n"}, "no contexts")
    monkeypatch.chdir(_project(tmp_path))

    code, out, err = _run(["--warehouse", str(repo)])

    assert code == 1
    assert out == ""
    assert f"error: no contexts/ directory at {sha} in warehouse" in err
