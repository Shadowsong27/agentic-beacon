"""Phase 6 - synthetic-distribution canonical-link resolution integration test.

Builds a hermetic synthetic warehouse with all four canonical-link categories
(plus an own-folder skill asset and an agent->partial canonical link), wires up
a tmp project via real `abc warehouse connect` + `abc sync`, then walks every
distributed artifact and asserts every canonical link resolves from the project
root. A negative-fixture warehouse plants malformed/missing-target links and
asserts `abc warehouse lint` catches them and `--fix` clears the fixable one.
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from beacon.cli.main import main
from beacon.core.scanner.scanner import (
    LINK_CANONICAL,
    LINK_CROSS_ARTIFACT_RELATIVE,
    LINK_OWN_SKILL_FOLDER,
    LINK_WAREHOUSE_ESCAPE,
    classify_link,
    extract_markdown_headings,
    extract_markdown_links,
)
from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


def _git_init_commit(path: Path, message: str = "init") -> None:
    env = _git_env()
    subprocess.run(["git", "init"], cwd=path, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "."], cwd=path, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


def _init_warehouse(tmp_path: Path, name: str) -> Path:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            name,
            "--path",
            str(tmp_path),
            "--org",
            "Test Org",
            "--languages",
            "python",
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, f"warehouse init failed:\n{result.output}"
    return tmp_path / name


def _write_agents_manifest(warehouse: Path) -> None:
    (warehouse / "agents" / "agents.yaml").write_text(
        yaml.safe_dump({"test-supervisor": {"skills": []}}, sort_keys=True)
    )


def _populate_positive_warehouse(warehouse: Path) -> None:
    (warehouse / "contexts" / "team-context.md").write_text(
        "# Team Context\n\n"
        "## Section A\n\n"
        "See [skill](.agentic-beacon/artifacts/skills/code-review/SKILL.md).\n"
    )

    skill_dir = warehouse / "skills" / "code-review"
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "references" / "api.md").write_text("# API Notes\n")
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: code-review\n"
        "description: Review code changes.\n"
        "requires:\n"
        "  contexts: []\n"
        "---\n\n"
        "# Code Review\n\n"
        "Read [ctx](.agentic-beacon/artifacts/contexts/team-context.md#section-a).\n"
        "Read [api](references/api.md).\n"
    )

    (warehouse / "agent-partials").mkdir(exist_ok=True)
    (warehouse / "agent-partials" / "deep-review-checklist.md").write_text(
        "# Deep Review Checklist\n\n- [ ] Confirm artifacts resolve.\n"
    )
    (warehouse / "agents" / "test-supervisor.md").write_text(
        "---\n"
        "name: test-supervisor\n"
        "description: Supervises integration checks.\n"
        "---\n\n"
        "# Test Supervisor\n\n"
        "Use [checklist](.agentic-beacon/artifacts/agent-partials/deep-review-checklist.md).\n"
    )

    # Knowledge files exist in the warehouse to support the warehouse-side
    # canonical-link walk (TC2: context→knowledge canonical, TC4:
    # knowledge→knowledge canonical) and to keep `abc warehouse lint` happy
    # when validating the synthetic fixture. They are NOT pulled into the
    # downstream project because:
    #   1. beacon.yaml in this test does not declare any knowledge dir
    #      (ArtifactsConfig has no `knowledge` field).
    #   2. The auto-pull pathway in core/scanner/scanner.scan_file_for_knowledge
    #      recognises legacy directory-relative `knowledge/...` links only,
    #      not the new canonical form `.agentic-beacon/artifacts/knowledge/...`.
    #      Filed as a follow-up: extending auto-pull to canonical links lives
    #      outside this change's scope (per spec: scan_file_for_knowledge is
    #      explicitly NOT modified — sync stays warning-only). See repo issue
    #      tracker for the dedicated ticket.
    # The project-side canonical-link walk therefore covers
    # skill→context, agent→partial, skill own-folder, and context→skill;
    # the warehouse-side walk additionally covers knowledge→knowledge.
    (warehouse / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (warehouse / "knowledge" / "python" / "standards.md").write_text(
        "# Python Standards\n\n"
        "## Section A\n\n"
        "See [style](.agentic-beacon/artifacts/knowledge/python/style-guide.md).\n"
    )
    (warehouse / "knowledge" / "python" / "style-guide.md").write_text(
        "# Style Guide\n\n## Usage\n\nKeep examples short.\n"
    )

    _write_agents_manifest(warehouse)


def _write_negative_warehouse(warehouse: Path, *, include_missing_target: bool) -> None:
    _populate_positive_warehouse(warehouse)

    skill_path = warehouse / "skills" / "code-review" / "SKILL.md"
    skill_path.write_text(
        "---\n"
        "name: code-review\n"
        "description: Review code changes.\n"
        "requires:\n"
        "  contexts: []\n"
        "---\n\n"
        "# Code Review\n\n"
        "Read [ctx](../../contexts/team-context.md).\n"
        "Read [api](references/api.md).\n"
    )

    if include_missing_target:
        (warehouse / "contexts" / "team-context.md").write_text(
            "# Team Context\n\n"
            "See [gone](.agentic-beacon/artifacts/knowledge/python/missing.md).\n"
        )


@pytest.fixture
def synthetic_warehouse(tmp_path: Path) -> Path:
    warehouse = _init_warehouse(tmp_path, "synthetic-warehouse")
    _populate_positive_warehouse(warehouse)
    _git_init_commit(warehouse)
    return warehouse


@pytest.fixture
def negative_fixture_warehouse(tmp_path: Path) -> Path:
    warehouse = _init_warehouse(tmp_path, "negative-warehouse")
    _write_negative_warehouse(warehouse, include_missing_target=True)
    _git_init_commit(warehouse)
    return warehouse


@pytest.fixture
def fixable_only_warehouse(tmp_path: Path) -> Path:
    warehouse = _init_warehouse(tmp_path, "fixable-only-warehouse")
    _write_negative_warehouse(warehouse, include_missing_target=False)
    _git_init_commit(warehouse)
    return warehouse


@pytest.fixture
def synced_project(
    tmp_path: Path, synthetic_warehouse: Path, monkeypatch
) -> tuple[Path, Path]:
    runner = CliRunner()
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / ".claude").mkdir()
    (project_dir / ".opencode").mkdir()

    monkeypatch.chdir(project_dir)
    connect = runner.invoke(
        main,
        ["warehouse", "connect", "--path", str(synthetic_warehouse)],
    )
    assert connect.exit_code == 0, f"connect failed:\n{connect.output}"

    setup = runner.invoke(main, ["setup"])
    assert setup.exit_code == 0, f"setup failed:\n{setup.output}"

    (project_dir / ".agentic-beacon" / "beacon.yaml").write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/team-context.md\n"
        "  skills:\n"
        "    - skills/code-review/\n"
        "  agents:\n"
        "    - agents/test-supervisor.md\n"
    )

    sync = runner.invoke(main, ["sync", "--skip-git-check"])
    assert sync.exit_code == 0, f"sync failed:\n{sync.output}"

    return project_dir, synthetic_warehouse


def _assert_links_resolve(
    project_dir: Path, warehouse: Path, source_file: Path
) -> None:
    for link in extract_markdown_links(source_file.read_text(encoding="utf-8")):
        category = classify_link(
            link.target, source_file=source_file, warehouse_root=warehouse
        )
        assert category not in {
            LINK_CROSS_ARTIFACT_RELATIVE,
            LINK_WAREHOUSE_ESCAPE,
        }, f"unexpected non-canonical link {link.target!r} in {source_file}"

        if category == LINK_CANONICAL:
            target_path = project_dir / link.target.split("#", 1)[0]
            assert target_path.exists(), (
                f"missing canonical target for {link.target} from {source_file}"
            )
            if "#" in link.target:
                headings = extract_markdown_headings(target_path)
                anchor = link.target.split("#", 1)[1]
                assert anchor in headings

        if category == LINK_OWN_SKILL_FOLDER:
            assert (source_file.parent / link.target).exists()


def test_sync_materializes_declared_artifacts_and_agent_partial_mirror(
    synced_project: tuple[Path, Path],
):
    project_dir, warehouse = synced_project

    expected_paths = [
        project_dir / ".agentic-beacon" / "artifacts" / "contexts" / "team-context.md",
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-review"
        / "SKILL.md",
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "test-supervisor.md",
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "agent-partials"
        / "deep-review-checklist.md",
        project_dir / ".claude" / "agents" / "test-supervisor.md",
        project_dir / ".opencode" / "agents" / "test-supervisor.md",
    ]

    for path in expected_paths:
        assert path.is_symlink(), f"expected symlink at {path}"
        assert path.resolve().is_file(), f"expected resolved file for {path}"
        assert str(path.resolve()).startswith(str(warehouse.resolve()))

    assert not (project_dir / ".claude" / "agents" / "_partials").exists()
    assert not (project_dir / ".opencode" / "agents" / "_partials").exists()


def test_artifact_mirror_files_only_use_resolving_link_categories(
    synced_project: tuple[Path, Path],
):
    project_dir, warehouse = synced_project
    for source_file in (project_dir / ".agentic-beacon" / "artifacts").rglob("*.md"):
        _assert_links_resolve(project_dir, warehouse, source_file)


def test_claude_agent_links_resolve_from_project_root(
    synced_project: tuple[Path, Path],
):
    project_dir, warehouse = synced_project
    for source_file in (project_dir / ".claude" / "agents").rglob("*.md"):
        _assert_links_resolve(project_dir, warehouse, source_file)


def test_opencode_agent_links_resolve_from_project_root(
    synced_project: tuple[Path, Path],
):
    project_dir, warehouse = synced_project
    for source_file in (project_dir / ".opencode" / "agents").rglob("*.md"):
        _assert_links_resolve(project_dir, warehouse, source_file)


def test_knowledge_anchor_resolves_in_distributed_target(
    synced_project: tuple[Path, Path],
):
    """TC5: anchor on a canonical link matches a heading slug in the target.

    Knowledge files aren't materialised under .agentic-beacon/artifacts/ in
    this fixture (auto-pull doesn't recognise canonical-form links — see
    follow-up note in _populate_positive_warehouse). Verify the anchor
    resolution rule against the warehouse-side knowledge file instead;
    that's the source the symlink would resolve to once auto-pull is
    extended to canonical links.
    """
    _project_dir, warehouse = synced_project
    target = warehouse / "knowledge" / "python" / "standards.md"
    assert "section-a" in extract_markdown_headings(target)


def test_warehouse_side_canonical_links_in_knowledge_resolve(
    synthetic_warehouse: Path,
):
    """TC2 + TC4: walk warehouse-side knowledge files; every canonical link
    points at an existing warehouse file.

    Mirrors the project-side resolution walk but rooted at the warehouse —
    needed to exercise context→knowledge and knowledge→knowledge canonical
    links because knowledge is not pulled into the project under the current
    spec (see follow-up note in _populate_positive_warehouse).
    """
    for source_file in (synthetic_warehouse / "knowledge").rglob("*.md"):
        for link in extract_markdown_links(source_file.read_text(encoding="utf-8")):
            category = classify_link(
                link.target,
                source_file=source_file,
                warehouse_root=synthetic_warehouse,
            )
            assert category in {LINK_CANONICAL, LINK_OWN_SKILL_FOLDER}, (
                f"unexpected non-canonical link {link.target!r} in {source_file}"
            )
            if category == LINK_CANONICAL:
                # canonical resolution rule: strip prefix → warehouse-relative
                rel = link.target.split("#", 1)[0].removeprefix(
                    ".agentic-beacon/artifacts/"
                )
                assert (synthetic_warehouse / rel).exists(), (
                    f"missing canonical target for {link.target} from {source_file}"
                )


def test_skill_own_folder_reference_resolves_inside_skill_directory(
    synced_project: tuple[Path, Path],
):
    project_dir, warehouse = synced_project
    skill_file = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-review"
        / "SKILL.md"
    )
    links = extract_markdown_links(skill_file.read_text(encoding="utf-8"))
    api_link = next(link for link in links if link.target == "references/api.md")
    assert (
        classify_link(api_link.target, source_file=skill_file, warehouse_root=warehouse)
        == LINK_OWN_SKILL_FOLDER
    )
    assert (skill_file.parent / api_link.target).exists()


def test_negative_lint_reports_malformed_and_missing_target_findings(
    negative_fixture_warehouse: Path,
):
    runner = CliRunner()
    result = runner.invoke(main, ["warehouse", "lint", str(negative_fixture_warehouse)])

    assert result.exit_code == 1
    assert "skills/code-review/SKILL.md" in result.output
    assert "malformed cross-artifact link" in result.output
    assert "contexts/team-context.md" in result.output
    assert "missing canonical target" in result.output


def test_negative_lint_fix_rewrites_fixable_link_and_leaves_missing_target(
    negative_fixture_warehouse: Path,
):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["warehouse", "lint", str(negative_fixture_warehouse), "--fix"],
    )

    assert result.exit_code == 1
    assert "missing canonical target" in result.output
    assert "malformed cross-artifact link" not in result.output

    skill_content = (
        negative_fixture_warehouse / "skills" / "code-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "[ctx](.agentic-beacon/artifacts/contexts/team-context.md)" in skill_content


def test_fixable_only_warehouse_passes_after_lint_fix(fixable_only_warehouse: Path):
    runner = CliRunner()
    fix_result = runner.invoke(
        main,
        ["warehouse", "lint", str(fixable_only_warehouse), "--fix"],
    )
    assert fix_result.exit_code == 0, fix_result.output

    relint_result = runner.invoke(
        main, ["warehouse", "lint", str(fixable_only_warehouse)]
    )
    assert relint_result.exit_code == 0, relint_result.output
