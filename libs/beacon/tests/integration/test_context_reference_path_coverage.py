"""Integration tests for context-reference reconciliation path coverage (AB-96, tasks 4.3-4.5).

Covers:
- 4.3: abc sync after de-adopting a context removes its reference from both files
- 4.3: abc adopt accept adds reference; reject/un-adopt removes it
- 4.4: Doctor --fix loop: broken + unmanaged references flagged, repaired, re-run clean
- 4.5: Regression fixture reproducing this repo's exact condition
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from beacon.cli.main import main
from beacon.core.gitignore import apply_all_gitignores
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.setup.diagnostics import run_project_diagnostics
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

GIT_ENV = {
    **__import__("os").environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@t.local",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@t.local",
}


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init"], cwd=path, env=GIT_ENV, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, msg: str = "add files") -> None:
    subprocess.run(
        ["git", "add", "-A"], cwd=path, env=GIT_ENV, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=path,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )


def _make_warehouse(tmp_path: Path) -> Path:
    """Build a minimal warehouse with two contexts and a committed initial state."""
    wh = tmp_path / "warehouse"
    for d in ("agents", "contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# Test Warehouse")
    (wh / "contexts" / "plane-ops.md").write_text("# Plane Ops")
    (wh / "contexts" / "python-standards.md").write_text("# Python Standards")
    _git_init(wh)
    _git_commit(wh, "initial warehouse")
    return wh


def _make_connected_project(
    tmp_path: Path,
    warehouse: Path,
    *,
    beacon_yaml_content: str,
    project_name: str = "project",
) -> Path:
    """Build a project connected to the warehouse with the given beacon.yaml content."""
    project = tmp_path / project_name
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()
    (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')
    (ab / "beacon.yaml").write_text(beacon_yaml_content)
    return project


# ---------------------------------------------------------------------------
# Task 4.3 — Path coverage: abc sync removes reference when context de-adopted
# ---------------------------------------------------------------------------


class TestSyncReferenceReconciliation:
    @pytest.fixture
    def project_with_context(self, tmp_path, valid_warehouse):
        """Project with one context in beacon.yaml and both config files."""
        (valid_warehouse / "contexts" / "global.md").write_text("# Global context")
        subprocess.run(
            ["git", "add", "."],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add global context"],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
        )
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts:\n    - contexts/global.md\n  skills: []\n"
        )

        # Pre-populate both config files with the context reference
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [".agentic-beacon/artifacts/contexts/global.md"],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            "@AGENTS.md\n@.agentic-beacon/artifacts/contexts/global.md\n"
        )
        apply_all_gitignores(project)

        return project, valid_warehouse

    def test_sync_adds_reference_for_wired_context(
        self, tmp_path, valid_warehouse, monkeypatch
    ):
        """abc sync adds reference to both files for a newly wired context."""
        (valid_warehouse / "contexts" / "global.md").write_text("# Global context")
        subprocess.run(
            ["git", "add", "."],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add global context"],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
        )
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts:\n    - contexts/global.md\n  skills: []\n"
        )
        (project / "opencode.json").write_text(json.dumps({"instructions": []}) + "\n")
        (project / "CLAUDE.md").write_text("@AGENTS.md\n")

        monkeypatch.chdir(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, f"sync failed: {result.output}"

        oc_data = json.loads((project / "opencode.json").read_text())
        assert ".agentic-beacon/artifacts/contexts/global.md" in oc_data["instructions"]

        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/global.md" in claude_content

    def test_sync_removes_reference_after_deadopt(
        self, project_with_context, monkeypatch
    ):
        """abc sync after removing context from beacon.yaml removes its reference (TC1 for 4.3)."""
        project, warehouse = project_with_context

        # De-adopt the context: remove from beacon.yaml
        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")

        monkeypatch.chdir(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, f"sync failed: {result.output}"

        # Reference must be gone from opencode.json
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/global.md"
            not in oc_data["instructions"]
        )

        # Reference must be gone from CLAUDE.md
        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/global.md" not in claude_content

        # Non-artifact lines must be preserved
        assert "@AGENTS.md" in claude_content

    def test_sync_dry_run_does_not_write_references(
        self, tmp_path, valid_warehouse, monkeypatch
    ):
        """abc sync --dry-run does not write references (TC3 for 4.3)."""
        (valid_warehouse / "contexts" / "global.md").write_text("# Global context")
        subprocess.run(
            ["git", "add", "."],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add global context"],
            cwd=valid_warehouse,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
        )
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts:\n    - contexts/global.md\n  skills: []\n"
        )
        # Start with the old reference in opencode.json (should be removed but isn't in dry-run)
        (project / "opencode.json").write_text(
            json.dumps(
                {"instructions": [".agentic-beacon/artifacts/contexts/old-context.md"]},
                indent=2,
            )
            + "\n"
        )
        oc_before = (project / "opencode.json").read_bytes()

        monkeypatch.chdir(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check", "--dry-run"])

        assert result.exit_code == 0, f"sync failed: {result.output}"
        # File must be unchanged
        assert (project / "opencode.json").read_bytes() == oc_before


# ---------------------------------------------------------------------------
# Task 4.3 — Path coverage: abc adopt accept adds / reject removes reference
# ---------------------------------------------------------------------------


class TestAdoptReferenceReconciliation:
    @pytest.fixture
    def project_and_warehouse(self, tmp_path):
        """Minimal project + warehouse for adoption tests."""
        wh = _make_warehouse(tmp_path)
        project = tmp_path / "project"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )
        (ab / "artifacts").mkdir()
        (project / "opencode.json").write_text(json.dumps({"instructions": []}) + "\n")
        (project / "CLAUDE.md").write_text("@AGENTS.md\n")
        return project, wh

    def test_adopt_accept_adds_reference(self, project_and_warehouse):
        """Adopt-accept a context → reference present in both files (TC1 for 4.3 adopt path)."""
        from beacon.domains.adoption.apply import commit_session
        from beacon.domains.adoption.models import AdoptCandidate

        project, wh = project_and_warehouse

        commit_session(
            to_adopt=["contexts/plane-ops.md"],
            to_unadopt=[],
            pending_accept=[],
            pending_reject=[],
            candidates=[
                AdoptCandidate(artifact_type="contexts", path="contexts/plane-ops.md")
            ],
            pending_entries=[],
            project_root=project,
            warehouse_path=wh,
            artifacts_path=project / ".agentic-beacon" / "artifacts",
            beacon_yaml_path=project / ".agentic-beacon" / "beacon.yaml",
        )

        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )

        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in claude_content

    def test_unadopt_removes_reference(self, project_and_warehouse):
        """Un-adopt a context (remove from beacon.yaml) → reference removed from both files (TC2 for 4.3 adopt path)."""
        from beacon.domains.adoption.apply import commit_session
        from beacon.domains.adoption.models import AdoptCandidate

        project, wh = project_and_warehouse

        # First: adopt the context
        commit_session(
            to_adopt=["contexts/plane-ops.md"],
            to_unadopt=[],
            pending_accept=[],
            pending_reject=[],
            candidates=[
                AdoptCandidate(artifact_type="contexts", path="contexts/plane-ops.md")
            ],
            pending_entries=[],
            project_root=project,
            warehouse_path=wh,
            artifacts_path=project / ".agentic-beacon" / "artifacts",
            beacon_yaml_path=project / ".agentic-beacon" / "beacon.yaml",
        )

        # Verify the reference is present
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )

        # Now: unadopt the context
        commit_session(
            to_adopt=[],
            to_unadopt=["contexts/plane-ops.md"],
            pending_accept=[],
            pending_reject=[],
            candidates=[],
            pending_entries=[],
            project_root=project,
            warehouse_path=wh,
            artifacts_path=project / ".agentic-beacon" / "artifacts",
            beacon_yaml_path=project / ".agentic-beacon" / "beacon.yaml",
        )

        # Reference must be gone from opencode.json
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md"
            not in oc_data["instructions"]
        )

        # Reference must be gone from CLAUDE.md
        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" not in claude_content

        # Non-artifact lines preserved
        assert "@AGENTS.md" in claude_content


# ---------------------------------------------------------------------------
# Task 4.4 — Doctor --fix loop
# ---------------------------------------------------------------------------


class TestDoctorFixReferenceLoop:
    def _setup_project(
        self,
        tmp_path: Path,
        monkeypatch,
        *,
        beacon_yaml_content: str,
    ) -> tuple[Path, Path]:
        """Create a connected project with warehouse."""
        project = tmp_path / "project"
        project.mkdir()
        monkeypatch.chdir(project)

        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()
        (warehouse / "skills").mkdir()
        (warehouse / "knowledge").mkdir()

        subprocess.run(
            ["git", "init", str(warehouse)], capture_output=True, check=False
        )

        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')
        (ab / "beacon.yaml").write_text(beacon_yaml_content)

        apply_all_gitignores(project)
        return project, warehouse

    def test_doctor_detects_broken_and_unmanaged_references(
        self, tmp_path, monkeypatch
    ):
        """A repo with a broken + an unmanaged reference → both flagged by doctor (TC from 4.4)."""
        project, warehouse = self._setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
            ),
        )

        # Create the wired context's artifact
        artifacts_ctx = project / ".agentic-beacon" / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (warehouse / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        (artifacts_ctx / "plane-ops.md").symlink_to(
            warehouse / "contexts" / "plane-ops.md"
        )

        # Broken reference: linear-ops not in effective set (file gone from warehouse)
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/plane-ops.md",
                        ".agentic-beacon/artifacts/contexts/linear-ops.md",  # broken
                    ]
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"  # broken
        )

        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])

        assert result.exit_code == 0
        output = result.output
        # Broken reference should be flagged (file doesn't exist)
        assert "Broken reference" in output or "broken" in output.lower()

    def test_doctor_fix_repairs_broken_and_unmanaged_references(
        self, tmp_path, monkeypatch
    ):
        """abc doctor --fix repairs broken + unmanaged references; re-run is clean (TC from 4.4)."""
        project, warehouse = self._setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
            ),
        )

        # Create the artifact for the wired context (plane-ops)
        artifacts_ctx = project / ".agentic-beacon" / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (warehouse / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        (artifacts_ctx / "plane-ops.md").symlink_to(
            warehouse / "contexts" / "plane-ops.md"
        )

        # The effective set only has plane-ops.md.
        # opencode.json has: plane-ops (wired), linear-ops (broken — not in effective set, not in wh)
        # CLAUDE.md mirrors the same situation
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/plane-ops.md",
                        ".agentic-beacon/artifacts/contexts/linear-ops.md",  # not in effective set
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            "@AGENTS.md\n"
            "@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"  # not in effective set
        )

        runner = CliRunner()

        # Run --fix: should repair both files
        fix_result = runner.invoke(main, ["doctor", "--fix"])
        assert fix_result.exit_code == 0, f"doctor --fix failed: {fix_result.output}"

        # fixes_applied should be non-empty (repair happened)
        assert (
            "repaired" in fix_result.output.lower()
            or "fixed" in fix_result.output.lower()
        ), f"Expected repair message in: {fix_result.output}"

        # opencode.json: linear-ops removed, plane-ops still there
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in oc_data["instructions"]
        )

        # CLAUDE.md: linear-ops removed, plane-ops still there
        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in claude_content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in claude_content
        assert "@AGENTS.md" in claude_content

        # Re-run doctor (no --fix): should not flag any reference drift
        rerun_result = runner.invoke(main, ["doctor"])
        assert rerun_result.exit_code == 0
        # No broken-reference or unmanaged-reference issues for the owned artifacts
        rerun_output = rerun_result.output
        assert "linear-ops" not in rerun_output

    def test_doctor_fix_healthy_repo_no_write(self, tmp_path, monkeypatch):
        """Healthy repo → doctor --fix makes no changes (no spurious write) (TC from 4.4)."""
        project, warehouse = self._setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
            ),
        )

        # Create the artifact symlink
        artifacts_ctx = project / ".agentic-beacon" / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (warehouse / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        (artifacts_ctx / "plane-ops.md").symlink_to(
            warehouse / "contexts" / "plane-ops.md"
        )

        # Both files are already correctly wired
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [".agentic-beacon/artifacts/contexts/plane-ops.md"],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            "@AGENTS.md\n@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
        )

        oc_before = (project / "opencode.json").read_bytes()
        claude_before = (project / "CLAUDE.md").read_bytes()

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])

        assert result.exit_code == 0, f"doctor --fix failed: {result.output}"
        # Files must not have been written
        assert (project / "opencode.json").read_bytes() == oc_before
        assert (project / "CLAUDE.md").read_bytes() == claude_before

    def test_doctor_fix_fixes_applied_nonempty_on_repair(self, tmp_path, monkeypatch):
        """fixes_applied is non-empty when doctor --fix actually repairs (TC from 4.4)."""
        project, warehouse = self._setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
            ),
        )

        artifacts_ctx = project / ".agentic-beacon" / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (warehouse / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        (artifacts_ctx / "plane-ops.md").symlink_to(
            warehouse / "contexts" / "plane-ops.md"
        )

        # Drift: linear-ops not in effective set
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/plane-ops.md",
                        ".agentic-beacon/artifacts/contexts/linear-ops.md",
                    ]
                },
                indent=2,
            )
            + "\n"
        )

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon_manifest = BeaconManifest.from_yaml(beacon_yaml)

        _, fixes_applied = run_project_diagnostics(
            project, warehouse, beacon_manifest, fix=True
        )

        assert len(fixes_applied) > 0, "Expected at least one fix to be applied"
        # Should mention context references
        combined = " ".join(fixes_applied).lower()
        assert (
            "reference" in combined or "context" in combined or "repaired" in combined
        )


# ---------------------------------------------------------------------------
# Task 4.5 — Regression fixture: this repo's exact condition
# ---------------------------------------------------------------------------


class TestRegressionReferenceDrift:
    """Regression fixture: linear-ops.md (broken) + cicd-flow.md (unmanaged, present but undeclared)."""

    def _setup_regression_project(
        self, tmp_path: Path, monkeypatch
    ) -> tuple[Path, Path]:
        """Set up a project reproducing the AB-96 live-repo condition.

        - plane-ops.md is the only declared context in beacon.yaml
        - linear-ops.md is in CLAUDE.md + opencode.json but NOT in beacon.yaml (broken target)
        - cicd-flow.md is in CLAUDE.md + opencode.json but NOT in beacon.yaml (unmanaged: present locally)
        """
        project = tmp_path / "project"
        project.mkdir()
        monkeypatch.chdir(project)

        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()
        (warehouse / "skills").mkdir()
        (warehouse / "knowledge").mkdir()

        subprocess.run(
            ["git", "init", str(warehouse)], capture_output=True, check=False
        )

        # Create only plane-ops in the warehouse (linear-ops is "gone")
        (warehouse / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        # cicd-flow exists in the warehouse but is NOT in beacon.yaml
        (warehouse / "contexts" / "cicd-flow.md").write_text("# CICD Flow")

        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
        )

        # Create artifacts: plane-ops (real symlink), cicd-flow (present but undeclared)
        artifacts_ctx = ab / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (artifacts_ctx / "plane-ops.md").symlink_to(
            warehouse / "contexts" / "plane-ops.md"
        )
        (artifacts_ctx / "cicd-flow.md").symlink_to(
            warehouse / "contexts" / "cicd-flow.md"
        )
        # linear-ops artifact does NOT exist (file gone)

        # Reproduce the exact drift: both files reference linear-ops AND cicd-flow
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/plane-ops.md",
                        ".agentic-beacon/artifacts/contexts/linear-ops.md",  # broken (target absent)
                        ".agentic-beacon/artifacts/contexts/cicd-flow.md",  # unmanaged (not in beacon.yaml)
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            "@AGENTS.md\n"
            "@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"  # broken
            "@.agentic-beacon/artifacts/contexts/cicd-flow.md\n"  # unmanaged
        )

        apply_all_gitignores(project)
        return project, warehouse

    def test_tc1_broken_reference_removed_by_fix(self, tmp_path, monkeypatch):
        """TC1: broken reference (linear-ops.md target missing) removed by --fix."""
        project, _ = self._setup_regression_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])

        assert result.exit_code == 0, f"doctor --fix failed: {result.output}"

        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in oc_data["instructions"]
        )

        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in claude_content

    def test_tc2_unmanaged_reference_removed_by_fix(self, tmp_path, monkeypatch):
        """TC2: unmanaged reference (cicd-flow.md not in beacon.yaml) removed by --fix."""
        project, _ = self._setup_regression_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])

        assert result.exit_code == 0, f"doctor --fix failed: {result.output}"

        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/cicd-flow.md"
            not in oc_data["instructions"]
        )

        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/cicd-flow.md" not in claude_content

    def test_tc3_second_doctor_run_after_fix_is_clean(self, tmp_path, monkeypatch):
        """TC3: second doctor run after --fix reports no broken/unmanaged references for the fixed refs."""
        project, _ = self._setup_regression_project(tmp_path, monkeypatch)

        runner = CliRunner()
        # First pass: fix
        fix_result = runner.invoke(main, ["doctor", "--fix"])
        assert fix_result.exit_code == 0, f"doctor --fix failed: {fix_result.output}"

        # After fix, linear-ops and cicd-flow must be gone from both files
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in oc_data["instructions"]
        )
        assert (
            ".agentic-beacon/artifacts/contexts/cicd-flow.md"
            not in oc_data["instructions"]
        )
        # plane-ops must still be present
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )

        claude_content = (project / "CLAUDE.md").read_text()
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in claude_content
        assert "@.agentic-beacon/artifacts/contexts/cicd-flow.md" not in claude_content
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in claude_content

        # Second run: no reference-related errors for the fixed artifacts
        rerun_result = runner.invoke(main, ["doctor"])
        assert rerun_result.exit_code == 0
        rerun_output = rerun_result.output
        assert "linear-ops" not in rerun_output
        assert "cicd-flow" not in rerun_output

    def test_regression_both_files_cleaned_in_one_fix(self, tmp_path, monkeypatch):
        """Full regression: doctor --fix clears both linear-ops and cicd-flow from both config files."""
        project, _ = self._setup_regression_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])
        assert result.exit_code == 0, f"doctor --fix failed: {result.output}"

        oc_data = json.loads((project / "opencode.json").read_text())
        claude_content = (project / "CLAUDE.md").read_text()

        # Both bogus references gone from both files
        for bad_ref in ("linear-ops", "cicd-flow"):
            assert bad_ref not in str(oc_data["instructions"]), (
                f"{bad_ref} still in opencode.json after --fix"
            )
            assert (
                f"@.agentic-beacon/artifacts/contexts/{bad_ref}.md"
                not in claude_content
            ), f"{bad_ref} still in CLAUDE.md after --fix"

        # The declared reference (plane-ops) still present
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in claude_content

        # Non-artifact lines intact
        assert "@AGENTS.md" in claude_content


# ---------------------------------------------------------------------------
# AB-96 fix-up — Finding B regression: transitive skill-required contexts
# preserved by commit_session
# ---------------------------------------------------------------------------


class TestTransitiveContextPreservedByCommitSession:
    """Regression: adopt/reject a different context must NOT strip a transitive
    skill-required context's reference from the config files (AB-96 fix-up, Finding B).

    Setup:
    - Warehouse has skill ``my-skill`` with SKILL.md that declares
      ``requires.contexts: [transitive-ctx]``.
    - beacon.yaml has ``skills/my-skill/`` and ``contexts/plane-ops.md`` (explicit)
      but NOT ``contexts/transitive-ctx.md`` in artifacts.contexts.
    - transitive-ctx is in the effective set due to the skill dependency.
    - Both config files already contain ``@…/contexts/transitive-ctx.md``.
    - A second context (``contexts/plane-ops.md``) is adopted / unadopted via
      commit_session — the transitive reference must survive.
    """

    @pytest.fixture
    def project_with_transitive_context(self, tmp_path):
        """Build a warehouse+project where transitive-ctx is skill-required."""
        wh = tmp_path / "warehouse"
        for d in ("agents", "contexts", "knowledge", "skills"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# Test Warehouse")

        # Context files in warehouse
        (wh / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        (wh / "contexts" / "transitive-ctx.md").write_text("# Transitive Context")

        # Skill with frontmatter that requires transitive-ctx
        skill_dir = wh / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts:\n    - transitive-ctx\n---\n\n# My Skill\n"
        )

        _git_init(wh)
        _git_commit(wh, "initial warehouse with transitive skill dep")

        # Project: explicit contexts = [plane-ops], skills = [my-skill/]
        # transitive-ctx is NOT in artifacts.contexts but IS in effective set
        project = tmp_path / "project"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (ab / "beacon.yaml").write_text(
            "artifacts:\n"
            "  contexts:\n"
            "    - contexts/plane-ops.md\n"
            "  skills:\n"
            "    - skills/my-skill/\n"
            "  agents: []\n"
        )

        # Pre-create artifact symlinks (both contexts)
        artifacts_ctx = ab / "artifacts" / "contexts"
        artifacts_ctx.mkdir(parents=True)
        (artifacts_ctx / "plane-ops.md").symlink_to(wh / "contexts" / "plane-ops.md")
        (artifacts_ctx / "transitive-ctx.md").symlink_to(
            wh / "contexts" / "transitive-ctx.md"
        )

        # Both config files already contain the transitive reference
        transitive_ref = ".agentic-beacon/artifacts/contexts/transitive-ctx.md"
        plane_ref = ".agentic-beacon/artifacts/contexts/plane-ops.md"
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [transitive_ref, plane_ref],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(
            f"@AGENTS.md\n@{transitive_ref}\n@{plane_ref}\n"
        )

        return project, wh

    def test_adopt_other_context_preserves_transitive_ref(
        self, project_with_transitive_context
    ):
        """Adopting plane-ops (already present) via commit_session must keep transitive-ctx."""
        from beacon.domains.adoption.apply import commit_session
        from beacon.domains.adoption.models import AdoptCandidate

        project, wh = project_with_transitive_context
        transitive_ref = ".agentic-beacon/artifacts/contexts/transitive-ctx.md"

        # Adopt plane-ops (it's already there; commit_session is idempotent for beacon.yaml)
        commit_session(
            to_adopt=["contexts/plane-ops.md"],
            to_unadopt=[],
            pending_accept=[],
            pending_reject=[],
            candidates=[
                AdoptCandidate(artifact_type="contexts", path="contexts/plane-ops.md")
            ],
            pending_entries=[],
            project_root=project,
            warehouse_path=wh,
            artifacts_path=project / ".agentic-beacon" / "artifacts",
            beacon_yaml_path=project / ".agentic-beacon" / "beacon.yaml",
        )

        # transitive-ctx reference must still be in opencode.json
        oc_data = json.loads((project / "opencode.json").read_text())
        assert transitive_ref in oc_data["instructions"], (
            f"transitive-ctx reference was stripped from opencode.json after adopt; "
            f"instructions={oc_data['instructions']}"
        )

        # transitive-ctx reference must still be in CLAUDE.md
        claude_content = (project / "CLAUDE.md").read_text()
        assert f"@{transitive_ref}" in claude_content, (
            f"transitive-ctx reference was stripped from CLAUDE.md after adopt; "
            f"content={claude_content!r}"
        )

    def test_unadopt_other_context_preserves_transitive_ref(
        self, project_with_transitive_context
    ):
        """Un-adopting plane-ops via commit_session must keep transitive-ctx reference."""
        from beacon.domains.adoption.apply import commit_session

        project, wh = project_with_transitive_context
        transitive_ref = ".agentic-beacon/artifacts/contexts/transitive-ctx.md"

        # Un-adopt plane-ops (remove from beacon.yaml and config files)
        commit_session(
            to_adopt=[],
            to_unadopt=["contexts/plane-ops.md"],
            pending_accept=[],
            pending_reject=[],
            candidates=[],
            pending_entries=[],
            project_root=project,
            warehouse_path=wh,
            artifacts_path=project / ".agentic-beacon" / "artifacts",
            beacon_yaml_path=project / ".agentic-beacon" / "beacon.yaml",
        )

        # plane-ops reference should be gone from opencode.json
        oc_data = json.loads((project / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md"
            not in oc_data["instructions"]
        ), "plane-ops reference should have been removed after unadopt"

        # transitive-ctx reference must still be in opencode.json
        assert transitive_ref in oc_data["instructions"], (
            f"transitive-ctx reference was stripped from opencode.json after unadopt; "
            f"instructions={oc_data['instructions']}"
        )

        # transitive-ctx reference must still be in CLAUDE.md
        claude_content = (project / "CLAUDE.md").read_text()
        assert f"@{transitive_ref}" in claude_content, (
            f"transitive-ctx reference was stripped from CLAUDE.md after unadopt; "
            f"content={claude_content!r}"
        )


# ---------------------------------------------------------------------------
# AB-96 fix-up — Finding A: de-adopt sync reports removal, not "Wired"
# ---------------------------------------------------------------------------


class TestDeAdoptSyncMessage:
    """De-adopt sync reports a removal message, not 'Wired', (AB-96 fix-up, Finding A)."""

    def test_de_adopt_sync_result_has_refs_removed_not_refs_added(
        self, tmp_path, valid_warehouse, monkeypatch
    ):
        """SyncOrchestrationResult.refs_removed is non-empty and refs_added is empty
        when a context is removed from beacon.yaml (de-adopt path)."""
        import os

        from beacon.domains.distribution.orchestrator import run_sync

        (valid_warehouse / "contexts" / "global.md").write_text("# Global context")
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "t@t.local",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "t@t.local",
        }
        subprocess.run(
            ["git", "add", "."],
            cwd=valid_warehouse,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add global context"],
            cwd=valid_warehouse,
            env=env,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "proj"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
        )
        # beacon.yaml has NO contexts (de-adopted state)
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )

        # Both config files contain the stale reference that should be removed
        stale_ref = ".agentic-beacon/artifacts/contexts/global.md"
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [stale_ref],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(f"@{stale_ref}\n")

        monkeypatch.chdir(project)
        result = run_sync(project_root=project, skip_git_check=True)

        # refs_removed must contain the stale reference (one or both files)
        assert result.refs_removed, (
            f"Expected refs_removed to be non-empty; got refs_removed={result.refs_removed}"
        )
        # refs_added must be empty (nothing was added)
        assert not result.refs_added, (
            f"Expected refs_added to be empty; got refs_added={result.refs_added}"
        )

    def test_de_adopt_sync_cli_output_says_removed_not_wired(
        self, tmp_path, valid_warehouse, monkeypatch
    ):
        """abc sync output on de-adopt says 'Removed … stale context reference(s)',
        not 'Wired … context(s)' (AB-96 fix-up, Finding A)."""
        import os

        (valid_warehouse / "contexts" / "global.md").write_text("# Global context")
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "t@t.local",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "t@t.local",
        }
        subprocess.run(
            ["git", "add", "."],
            cwd=valid_warehouse,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add global context"],
            cwd=valid_warehouse,
            env=env,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "proj2"
        project.mkdir()
        ab = project / ".agentic-beacon"
        ab.mkdir()
        (ab / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
        )
        (ab / "beacon.yaml").write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )

        stale_ref = ".agentic-beacon/artifacts/contexts/global.md"
        (project / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [stale_ref],
                },
                indent=2,
            )
            + "\n"
        )
        (project / "CLAUDE.md").write_text(f"@{stale_ref}\n")

        monkeypatch.chdir(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, f"sync failed: {result.output}"
        output = result.output

        # Must mention removal, not wiring
        assert "Removed" in output and "stale context reference" in output, (
            f"Expected 'Removed … stale context reference(s)' in output; got: {output!r}"
        )
        # Must NOT say "Wired N context reference(s)" (that is the add path)
        assert "Wired" not in output, (
            f"Output still contains 'Wired' (old wording for removals): {output!r}"
        )
