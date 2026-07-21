"""Unit tests for repair_reference_drift no-op guard paths and basic behavior (AB-96).

Covers:
- The no-op guards: beacon_manifest is None, warehouse_path is None, ResolutionFailure
- TC1: broken + unmanaged reference -> reconciled, fix lines returned
- TC2: healthy repo -> returns [] and writes nothing
"""

from __future__ import annotations

import json
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.setup.diagnostics import repair_reference_drift

# ---------------------------------------------------------------------------
# No-op guard paths
# ---------------------------------------------------------------------------


class TestRepairReferenceDriftNoOpGuards:
    def test_returns_empty_when_beacon_manifest_is_none(self, tmp_path):
        """Returns [] immediately when beacon_manifest is None."""
        result = repair_reference_drift(tmp_path, None, tmp_path / "warehouse")
        assert result == []

    def test_returns_empty_when_warehouse_path_is_none(self, tmp_path):
        """Returns [] immediately when warehouse_path is None."""
        # Use a real manifest — warehouse_path guard fires first, no artifacts access needed
        beacon_yaml = tmp_path / "beacon.yaml"
        beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")
        manifest = BeaconManifest.from_yaml(beacon_yaml)
        result = repair_reference_drift(tmp_path, manifest, None)
        assert result == []

    def test_returns_empty_when_both_none(self, tmp_path):
        """Returns [] immediately when both are None."""
        result = repair_reference_drift(tmp_path, None, None)
        assert result == []

    def _make_minimal_manifest(self, tmp_path: Path) -> BeaconManifest:
        """Build a real BeaconManifest with one context entry for guard tests."""
        # Uses a context name that will NOT resolve in any warehouse (missing file)
        # so compute_effective_set returns ResolutionFailure naturally.
        beacon_yaml = tmp_path / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n  contexts:\n    - contexts/nonexistent-ctx.md\n  skills: []\n"
        )
        return BeaconManifest.from_yaml(beacon_yaml)

    def test_returns_empty_when_resolution_failure(self, tmp_path):
        """Returns [] when compute_effective_set returns a ResolutionFailure.

        Uses a real manifest whose context doesn't exist in the (empty) warehouse,
        so compute_effective_set naturally returns ResolutionFailure.
        """
        # Create a warehouse directory that is empty (no contexts/)
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        manifest = self._make_minimal_manifest(tmp_path)

        result = repair_reference_drift(tmp_path, manifest, warehouse)
        assert result == []

    def test_no_write_when_resolution_failure(self, tmp_path):
        """No files are written when compute_effective_set returns ResolutionFailure."""
        (tmp_path / "opencode.json").write_text(
            json.dumps(
                {"instructions": [".agentic-beacon/artifacts/contexts/some-ref.md"]},
                indent=2,
            )
            + "\n"
        )
        before = (tmp_path / "opencode.json").read_bytes()

        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        manifest = self._make_minimal_manifest(tmp_path)

        result = repair_reference_drift(tmp_path, manifest, warehouse)

        assert result == []
        assert (tmp_path / "opencode.json").read_bytes() == before


# ---------------------------------------------------------------------------
# Functional behavior: real BeaconManifest + warehouse
# ---------------------------------------------------------------------------


class TestRepairReferenceDriftBehavior:
    def _make_warehouse(self, tmp_path: Path) -> Path:
        """Minimal warehouse with one context."""
        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        (wh / "skills").mkdir(parents=True)
        (wh / "contexts" / "plane-ops.md").write_text("# Plane Ops")
        return wh

    def test_tc1_broken_and_unmanaged_reference_reconciled(self, tmp_path):
        """TC1: repo with a broken + an unmanaged reference -> both reconciled, fix lines returned."""
        wh = self._make_warehouse(tmp_path)

        # beacon.yaml: only plane-ops declared
        beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.parent.mkdir(parents=True)
        beacon_yaml.write_text(
            "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
        )
        manifest = BeaconManifest.from_yaml(beacon_yaml)

        # opencode.json: contains plane-ops (desired) + linear-ops (not desired)
        (tmp_path / "opencode.json").write_text(
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

        result = repair_reference_drift(tmp_path, manifest, wh)

        # Fix lines must be returned (something was repaired)
        assert len(result) > 0
        combined = " ".join(result).lower()
        assert (
            "repaired" in combined or "reference" in combined or "removed" in combined
        )

        # linear-ops must be gone from opencode.json
        oc_data = json.loads((tmp_path / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in oc_data["instructions"]
        )
        assert (
            ".agentic-beacon/artifacts/contexts/plane-ops.md" in oc_data["instructions"]
        )

    def test_tc2_healthy_repo_returns_empty_and_no_write(self, tmp_path):
        """TC2: healthy repo -> returns [] and writes nothing."""
        wh = self._make_warehouse(tmp_path)

        beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.parent.mkdir(parents=True)
        beacon_yaml.write_text(
            "artifacts:\n  contexts:\n    - contexts/plane-ops.md\n  skills: []\n"
        )
        manifest = BeaconManifest.from_yaml(beacon_yaml)

        # opencode.json already has the correct reference
        (tmp_path / "opencode.json").write_text(
            json.dumps(
                {"instructions": [".agentic-beacon/artifacts/contexts/plane-ops.md"]},
                indent=2,
            )
            + "\n"
        )
        before = (tmp_path / "opencode.json").read_bytes()

        result = repair_reference_drift(tmp_path, manifest, wh)

        assert result == []
        assert (tmp_path / "opencode.json").read_bytes() == before
