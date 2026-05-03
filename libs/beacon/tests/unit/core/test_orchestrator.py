"""Unit tests for sync orchestration."""

import pytest
from beacon.core.exceptions import BeaconSyncError
from beacon.domains.distribution.orchestrator import run_sync


def test_run_sync_rejects_contribute_and_discard_flags_together():
    """run_sync enforces mutual exclusivity before any filesystem work."""
    with pytest.raises(BeaconSyncError) as exc_info:
        run_sync(contribute_local=True, discard_local=True)

    assert "mutually exclusive" in str(exc_info.value)
