"""Unit tests for sync orchestration."""

import pytest
from beacon.core.exceptions import BeaconSyncError
from beacon.domains.distribution.orchestrator import run_sync


def test_run_sync_rejects_contribute_and_discard_flags_together():
    """run_sync enforces mutual exclusivity before any filesystem work."""
    with pytest.raises(BeaconSyncError) as exc_info:
        run_sync(contribute_local=True, discard_local=True)

    assert "mutually exclusive" in str(exc_info.value)


def test_dry_run_does_not_call_wiring_or_global_install(tmp_path, monkeypatch):
    """Dry-run previews symlinks without mutating project or global agent dirs."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "contexts" / "team.md").write_text("# Team\n")
    (warehouse / "skills" / "review").mkdir(parents=True)
    (warehouse / "skills" / "review" / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# Review\n"
    )

    project = tmp_path / "project"
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir(parents=True)
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  skills:\n"
        "    - skills/review\n"
        "  contexts:\n"
        "    - contexts/team.md\n"
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run called a side-effecting wiring function")

    monkeypatch.setattr(
        "beacon.domains.distribution.orchestrator.install_bundled_skills_globally",
        fail_if_called,
    )
    monkeypatch.setattr(
        "beacon.domains.distribution.orchestrator.wire_bundled_skills_per_project",
        fail_if_called,
    )
    monkeypatch.setattr(
        "beacon.domains.distribution.orchestrator.wire_contexts_opencode",
        fail_if_called,
    )
    monkeypatch.setattr(
        "beacon.domains.distribution.orchestrator.wire_contexts_claudecode",
        fail_if_called,
    )
    monkeypatch.setattr(
        "beacon.domains.distribution.orchestrator.wire_skills_post_sync",
        fail_if_called,
    )
    monkeypatch.chdir(project)

    result = run_sync(project, dry_run=True, skip_git_check=True)

    assert result.dry_run is True
    assert result.summary.created == 2
    assert not (beacon_dir / "artifacts" / "contexts" / "team.md").exists()
