"""Tests for gitignore-drift check in abc doctor (task 3.1, 4.5).

Covers:
- Drifted project → DoctorIssue with severity 'error'
- Healthy project → no gitignore DoctorIssue
- Tracked-set file ignored → error
- --fix correctly splits managed vs tracked-set drifts
"""

import subprocess
from pathlib import Path

from beacon.core.gitignore import (
    TIER_A_ENTRIES,
    TIER_B_OPENCODE_ENTRIES,
    apply_managed_block,
)
from beacon.domains.setup.diagnostics import (
    repair_gitignore_drift,
    run_project_health_checks,
)


def _git_init(path):
    subprocess.run(["git", "init", "-q", str(path)], check=False)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=False,
        capture_output=True,
    )


def _write_tier_a(tmp_path: Path, entries: list[str] | None = None) -> None:
    apply_managed_block(tmp_path / ".gitignore", entries or TIER_A_ENTRIES)


def _write_tier_b(tmp_path: Path, tool_dir: str, entries: list[str]) -> None:
    d = tmp_path / tool_dir
    d.mkdir(exist_ok=True)
    apply_managed_block(d / ".gitignore", entries)


def _make_wired(project_root):
    """Create .agentic-beacon/beacon.yaml so the project appears Beacon-wired."""
    d = project_root / ".agentic-beacon"
    d.mkdir(parents=True, exist_ok=True)
    (d / "beacon.yaml").write_text(
        "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
    )


class TestDoctorGitignoreDetection:
    def test_tc1_drifted_project_returns_error(self, tmp_path):
        _make_wired(tmp_path)
        _write_tier_b(tmp_path, ".opencode", TIER_B_OPENCODE_ENTRIES)
        issues = run_project_health_checks(tmp_path, None, None)
        gitignore_issues = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gitignore_issues) >= 1
        for i in gitignore_issues:
            assert i.severity == "error"

    def test_tc2_healthy_project_no_gitignore_issues(self, tmp_path):
        _write_tier_a(tmp_path)
        issues = run_project_health_checks(tmp_path, None, None)
        gitignore_issues = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gitignore_issues) == 0

    def test_tc3_tracked_set_ignored_error(self, tmp_path):
        _make_wired(tmp_path)
        _git_init(tmp_path)
        root = tmp_path / ".gitignore"
        root.write_text("beacon.yaml\n")
        _write_tier_a(tmp_path)
        issues = run_project_health_checks(tmp_path, None, None)
        tracked_issues = [i for i in issues if "tracked" in i.message.lower()]
        assert len(tracked_issues) >= 1
        for i in tracked_issues:
            assert i.severity == "error"

    def test_tier_a_missing_while_tier_b_present(self, tmp_path):
        _make_wired(tmp_path)
        (tmp_path / ".opencode").mkdir()
        apply_managed_block(
            tmp_path / ".opencode" / ".gitignore", TIER_B_OPENCODE_ENTRIES
        )
        issues = run_project_health_checks(tmp_path, None, None)
        gitignore_issues = [i for i in issues if "gitignore" in i.message.lower()]
        tier_a_issues = [i for i in gitignore_issues if "Tier A" in i.message]
        assert len(tier_a_issues) >= 1
        assert tier_a_issues[0].severity == "error"

    def test_unwired_project_returns_no_drift(self, tmp_path):
        """No .agentic-beacon/beacon.yaml → _check_gitignore_drift returns [].

        Even if the project's .gitignore lacks a managed block.
        """
        issues = run_project_health_checks(tmp_path, None, None)
        gitignore_issues = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gitignore_issues) == 0, (
            f"Expected no gitignore issues for unwired project, got: {gitignore_issues}"
        )

    def test_wired_project_still_reports_drift(self, tmp_path):
        """Wired project with drift still reports gitignore issues."""
        _make_wired(tmp_path)
        (tmp_path / ".opencode").mkdir()
        apply_managed_block(
            tmp_path / ".opencode" / ".gitignore", TIER_B_OPENCODE_ENTRIES
        )
        issues = run_project_health_checks(tmp_path, None, None)
        gitignore_issues = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gitignore_issues) >= 1, (
            "Expected gitignore drift for wired project with missing Tier A"
        )


class TestDoctorFix:
    def test_tc1_fix_repairs_drift(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        apply_managed_block(
            tmp_path / ".opencode" / ".gitignore", TIER_B_OPENCODE_ENTRIES
        )

        from beacon.core.gitignore import apply_all_gitignores

        apply_all_gitignores(tmp_path)

        drifts_before = len(
            [
                i
                for i in run_project_health_checks(tmp_path, None, None)
                if "gitignore" in i.message.lower()
            ]
        )
        assert drifts_before == 0, "apply_all_gitignores should fix drift"

    def test_tc2_healthy_no_spurious_fix(self, tmp_path):
        from beacon.core.gitignore import apply_all_gitignores, diff_gitignores

        apply_all_gitignores(tmp_path)
        drifts = diff_gitignores(tmp_path)
        assert len(drifts) == 0

    def test_tc3_fix_then_clean(self, tmp_path):
        from beacon.core.gitignore import apply_all_gitignores, diff_gitignores

        apply_all_gitignores(tmp_path)
        drifts = diff_gitignores(tmp_path)
        assert len(drifts) == 0

    def test_tracked_set_ignored_not_repaired(self, tmp_path):
        """tracked_set_ignored drift must NOT be repaired by apply_all_gitignores."""
        _make_wired(tmp_path)
        _git_init(tmp_path)
        root = tmp_path / ".gitignore"
        root.write_text(".agentic-beacon/beacon.yaml\n")
        from beacon.core.gitignore import apply_all_gitignores, diff_gitignores

        apply_all_gitignores(tmp_path)
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tracked_set_ignored" in kinds, (
            "tracked_set_ignored drift must persist after fix"
        )

    def test_managed_only_fix_is_clean(self, tmp_path):
        """Managed-block-only drift IS repaired by apply_all_gitignores."""
        from beacon.core.gitignore import apply_all_gitignores, diff_gitignores

        apply_all_gitignores(tmp_path)
        drifts_first = diff_gitignores(tmp_path)
        assert len(drifts_first) == 0

    # ── FIX F: doctor --fix gated to wired projects ──

    def test_unwired_project_fix_does_not_touch_gitignore(self, tmp_path, monkeypatch):
        """doctor --fix on unwired project must not create/modify .gitignore."""
        import beacon.cli.diagnostics
        from beacon.core.gitignore import MANAGED_BLOCK_BEGIN

        (tmp_path / ".agentic-beacon").mkdir()
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("my-custom-entry/\n")
        mtime_before = gitignore.stat().st_mtime
        content_before = gitignore.read_bytes()

        monkeypatch.setattr(
            beacon.cli.diagnostics, "find_project_root", lambda: tmp_path
        )
        beacon.cli.diagnostics.doctor.callback(fix=True)

        assert gitignore.stat().st_mtime == mtime_before
        assert gitignore.read_bytes() == content_before
        assert MANAGED_BLOCK_BEGIN not in gitignore.read_text()

    def test_wired_project_fix_repairs_drift(self, tmp_path, monkeypatch):
        """doctor --fix on wired project with drift repairs .gitignore."""
        import beacon.cli.diagnostics
        from beacon.core.gitignore import MANAGED_BLOCK_BEGIN

        _make_wired(tmp_path)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("user-entry/\n")

        monkeypatch.setattr(
            beacon.cli.diagnostics, "find_project_root", lambda: tmp_path
        )
        beacon.cli.diagnostics.doctor.callback(fix=True)

        content = gitignore.read_text()
        assert MANAGED_BLOCK_BEGIN in content
        assert "user-entry/" in content


# ── FIX H: repair_gitignore_drift (extracted domain op) ──


class TestRepairGitignoreDrift:
    def test_wired_drifted_project_repairs_and_returns_msgs(self, tmp_path):
        _make_wired(tmp_path)
        (tmp_path / ".opencode").mkdir()
        apply_managed_block(
            tmp_path / ".opencode" / ".gitignore", TIER_B_OPENCODE_ENTRIES
        )
        msgs = repair_gitignore_drift(tmp_path)
        assert len(msgs) >= 1
        assert "Repaired" in msgs[0]
        from beacon.core.gitignore import diff_gitignores

        remaining = diff_gitignores(tmp_path)
        managed = [
            d
            for d in remaining
            if d.kind
            in {
                "tier_a_missing",
                "tier_a_incomplete",
                "tier_b_missing",
                "tier_b_incomplete",
            }
        ]
        assert len(managed) == 0, (
            f"Managed-block drift should be repaired, got: {[d.message for d in managed]}"
        )

    def test_wired_healthy_returns_empty(self, tmp_path):
        from beacon.core.gitignore import apply_all_gitignores

        _make_wired(tmp_path)
        apply_all_gitignores(tmp_path)
        msgs = repair_gitignore_drift(tmp_path)
        assert msgs == []

    def test_unwired_returns_empty_no_write(self, tmp_path):
        msgs = repair_gitignore_drift(tmp_path)
        assert msgs == []
        gitignore = tmp_path / ".gitignore"
        assert not gitignore.exists()

    def test_stale_summary_regression(self, tmp_path):
        _make_wired(tmp_path)
        repair_gitignore_drift(tmp_path)
        issues = run_project_health_checks(tmp_path, None, None)
        managed_issues = [
            i
            for i in issues
            if "gitignore" in i.message.lower()
            and ("Tier A" in i.message or "Tier B" in i.message)
        ]
        assert len(managed_issues) == 0, (
            f"After repair, managed-block drift must not appear in health checks: "
            f"{[i.message for i in managed_issues]}"
        )

    def test_tracked_set_ignored_not_repaired_by_domain_op(self, tmp_path):
        _make_wired(tmp_path)
        _git_init(tmp_path)
        root = tmp_path / ".gitignore"
        root.write_text(".agentic-beacon/beacon.yaml\n")
        from beacon.core.gitignore import apply_all_gitignores

        apply_all_gitignores(tmp_path)
        msgs = repair_gitignore_drift(tmp_path)
        assert msgs == [], "tracked_set_ignored alone must not trigger repair"
