"""Integration tests: the Claude approval key is the main checkout root, via real git."""

import subprocess

import pytest
from beacon.domains.setup.claude_approval import resolve_claude_project_root

pytestmark = pytest.mark.integration

GIT_ID = ["-c", "user.name=test", "-c", "user.email=test@example.com"]


@pytest.fixture
def main_checkout(tmp_path):
    root = tmp_path / "main"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", *GIT_ID, "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=root,
        check=True,
    )
    return root


def test_linked_worktree_resolves_to_main_checkout(main_checkout, tmp_path):
    worktree = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-q", str(worktree), "-b", "wt-branch"],
        cwd=main_checkout,
        check=True,
    )

    assert resolve_claude_project_root(worktree) == main_checkout.resolve()


def test_subdirectory_resolves_to_main_checkout(main_checkout):
    subdir = main_checkout / "pkg" / "inner"
    subdir.mkdir(parents=True)

    assert resolve_claude_project_root(subdir) == main_checkout.resolve()


def test_non_git_directory_falls_back_to_itself(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    assert resolve_claude_project_root(plain) == plain.resolve()
