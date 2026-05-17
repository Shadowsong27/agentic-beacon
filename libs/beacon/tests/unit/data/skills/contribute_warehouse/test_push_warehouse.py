"""Unit tests for push_warehouse.py (Finding 4 fix-up: shlex.quote).

Tests verify:
- Recovery command quotes paths containing spaces so a shlex round-trip
  recovers the original arguments.
- Smoke test: success path against a fixture warehouse with a bare remote.
"""

from __future__ import annotations

import importlib.util
import os
import shlex
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

_SKILLS_DIR = Path(__file__).resolve().parents[5] / "src" / "beacon" / "data" / "skills"
_SCRIPT_PATH = _SKILLS_DIR / "contribute-warehouse" / "scripts" / "push_warehouse.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("push_warehouse", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_env():
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


def _make_git_repo(path: Path) -> None:
    """Init a git repo with an initial empty commit."""
    env = _git_env()
    subprocess.run(["git", "init"], cwd=path, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


class TestRecoveryCommandQuoting:
    """Finding 4: recovery command must quote paths with spaces."""

    def test_recovery_command_quotes_path_with_spaces(self, tmp_path, capsys):
        """Warehouse path with spaces is shell-quoted; shlex round-trip recovers args."""
        mod = _load_script()

        # Create a warehouse at a path containing spaces
        spaced = tmp_path / "my warehouse"
        spaced.mkdir()
        _make_git_repo(spaced)

        # Patch get_current_branch to return a branch name with a space too
        branch_with_space = "feature/foo bar"
        with patch.object(mod, "get_current_branch", return_value=branch_with_space):
            # Patch subprocess.run for the push call to simulate failure
            class _FakeResult:
                returncode = 1
                stderr = "simulated push failure"

            with patch("subprocess.run", return_value=_FakeResult()):
                with pytest.raises(SystemExit) as exc_info:
                    mod.push(spaced)
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        recovery_cmd = captured.out.strip()

        # The recovery command must be parseable by shlex.split
        tokens = shlex.split(recovery_cmd)
        assert tokens, f"shlex.split returned empty for: {recovery_cmd!r}"

        # Round-trip: the warehouse path token and branch token must survive
        # git -C <quoted-warehouse> push origin <quoted-branch>
        assert "git" in tokens
        warehouse_token = tokens[tokens.index("-C") + 1]
        assert warehouse_token == str(spaced), (
            f"Warehouse path not preserved after shlex round-trip. "
            f"Expected {str(spaced)!r}, got {warehouse_token!r}"
        )

        # Branch should also be preserved
        assert branch_with_space in tokens, (
            f"Branch {branch_with_space!r} not found in tokens: {tokens}"
        )

    def test_recovery_command_simple_path_unquoted_or_quoted(self, tmp_path, capsys):
        """Simple path without spaces: round-trip still works (may or may not quote)."""
        mod = _load_script()

        simple = tmp_path / "warehouse"
        simple.mkdir()
        _make_git_repo(simple)

        with patch.object(mod, "get_current_branch", return_value="main"):

            class _FakeResult:
                returncode = 1
                stderr = "simulated failure"

            with patch("subprocess.run", return_value=_FakeResult()):
                with pytest.raises(SystemExit) as exc_info:
                    mod.push(simple)
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        recovery_cmd = captured.out.strip()
        tokens = shlex.split(recovery_cmd)
        warehouse_token = tokens[tokens.index("-C") + 1]
        assert warehouse_token == str(simple)


class TestPushSmoke:
    """Smoke test: success path with a real bare remote."""

    def test_push_success_with_bare_remote(self, tmp_path, capsys):
        """Push to a bare local remote succeeds and exits 0."""
        mod = _load_script()
        env = _git_env()

        # Create bare upstream
        bare = tmp_path / "upstream.git"
        bare.mkdir()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=bare,
            env=env,
            check=True,
            capture_output=True,
        )

        # Create warehouse with remote
        wh = tmp_path / "warehouse"
        wh.mkdir()
        _make_git_repo(wh)
        subprocess.run(
            ["git", "-C", str(wh), "remote", "add", "origin", str(bare)],
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "push", "-u", "origin", "HEAD"],
            env=env,
            check=True,
            capture_output=True,
        )

        # Make a new commit so there is something to push
        (wh / "file.txt").write_text("hello\n")
        subprocess.run(
            ["git", "-C", str(wh), "add", "file.txt"],
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "add file"],
            env=env,
            check=True,
            capture_output=True,
        )

        # Now test the push function — should not raise SystemExit
        mod.push(wh)
        captured = capsys.readouterr()
        assert "Push succeeded" in captured.out or captured.out.strip() != ""
