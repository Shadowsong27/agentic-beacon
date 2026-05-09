"""Unit test for RegularFileConflictError handler in the sync CLI."""

import re
from pathlib import Path
from unittest.mock import patch

from beacon.core.exceptions import AgentWireConflict, RegularFileConflictError
from click.testing import CliRunner


def test_sync_regular_file_conflict_exits_1(tmp_path: Path) -> None:
    """sync exits 1 and renders the conflict path when run_sync raises RegularFileConflictError."""
    from beacon.cli.sync import sync

    dest = tmp_path / ".claude" / "agents" / "spec-planner.md"
    conflict = AgentWireConflict(
        dest=dest, agent_name="spec-planner", tool="claudecode"
    )
    error = RegularFileConflictError(conflicts=[conflict])

    runner = CliRunner()
    with patch(
        "beacon.cli.sync.run_sync",
        side_effect=error,
    ):
        result = runner.invoke(sync)

    assert result.exit_code == 1
    assert "Cannot wire 1 agent" in result.output
    # Rich wraps long paths at terminal width on CI (no TTY). Normalize whitespace
    # before substring search so wrap-induced breaks don't split the path.
    flat = re.sub(r"\s+", "", result.output)
    assert "spec-planner.md" in flat
