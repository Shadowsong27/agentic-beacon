"""Tests for the managed-block gitignore engine (core/gitignore.py).

Covers:
- apply_managed_block: fresh-file, stale-body regen, idempotent (task 4.1)
- Surgical migration of legacy blocks (task 4.2)
- Tier B entry-set regression lock (task 4.3)
- read_managed_block and apply_all_gitignores (tasks 1.4, 4.4)
- diff_gitignores (task 4.5)
"""

import subprocess

from beacon.core.gitignore import (
    MANAGED_BLOCK_BEGIN,
    MANAGED_BLOCK_END,
    TIER_A_ENTRIES,
    TIER_B_CLAUDE_ENTRIES,
    TIER_B_OPENCODE_ENTRIES,
    apply_all_gitignores,
    apply_managed_block,
    diff_gitignores,
    read_managed_block,
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


# ═════════════════════════════════════════════════════════════
# 1.2 apply_managed_block — fresh, regen, idempotent
# ═════════════════════════════════════════════════════════════


class TestApplyManagedBlock:
    def test_tc1_no_gitignore_creates_block(self, tmp_path):
        path = tmp_path / ".gitignore"
        entries = ["entry-a", "entry-b"]
        apply_managed_block(path, entries)
        assert path.exists()
        content = path.read_text()
        assert MANAGED_BLOCK_BEGIN in content
        assert MANAGED_BLOCK_END in content
        assert "entry-a" in content
        assert "entry-b" in content
        # Block is first-class content
        assert content.strip().startswith(MANAGED_BLOCK_BEGIN)
        assert content.strip().endswith(MANAGED_BLOCK_END)

    def test_tc2_idempotent_reapply(self, tmp_path):
        path = tmp_path / ".gitignore"
        entries = ["entry-a", "entry-b"]
        apply_managed_block(path, entries)
        first = path.read_bytes()
        apply_managed_block(path, entries)
        second = path.read_bytes()
        assert first == second

    def test_tc3_stale_body_regenerated(self, tmp_path):
        path = tmp_path / ".gitignore"
        apply_managed_block(path, ["entry-a", "entry-b"])
        # Now re-apply with different entries
        apply_managed_block(path, ["entry-c", "entry-d"])
        content = path.read_text()
        assert "entry-a" not in content
        assert "entry-b" not in content
        assert "entry-c" in content
        assert "entry-d" in content
        # Out-of-block content preserved
        assert content.count(MANAGED_BLOCK_BEGIN) == 1

    def test_tc3_preserves_out_of_block_content(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text("user-line\n")
        apply_managed_block(path, ["entry-a"])
        content = path.read_text()
        assert "user-line" in content
        body = read_managed_block(path)
        assert body == ["entry-a"]

    def test_tc4_no_trailing_newline(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text("last-line")
        apply_managed_block(path, ["entry-a"])
        content = path.read_text()
        assert content.endswith("\n")

    def test_tc5_empty_entries(self, tmp_path):
        path = tmp_path / ".gitignore"
        apply_managed_block(path, [])
        content = path.read_text()
        assert MANAGED_BLOCK_BEGIN in content
        assert MANAGED_BLOCK_END in content
        body = read_managed_block(path)
        assert body == []


# ═════════════════════════════════════════════════════════════
# 1.3 Surgical migration tests
# ═════════════════════════════════════════════════════════════


class TestMigration:
    def _legacy_content(
        self, managed_entries: list[str], unknown_entries: list[str]
    ) -> str:
        lines = ["# Agentic Beacon"]
        lines.extend(managed_entries)
        lines.extend(unknown_entries)
        return "\n".join(lines) + "\n"

    def test_tc1_migration_dedup_and_preserve(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text(
            "node_modules/\n"
            "# Agentic Beacon\n"
            ".agentic-beacon/config.toml\n"
            ".agentic-beacon/artifacts/\n"
            ".agentic-beacon/.legacy-migrated\n"
            "sample-warehouse/\n"
        )
        apply_managed_block(path, TIER_A_ENTRIES)
        content = path.read_text()
        assert "# Agentic Beacon" not in content
        assert ".agentic-beacon/.legacy-migrated" in content
        assert "sample-warehouse/" in content
        assert "node_modules/" in content
        body = read_managed_block(path)
        assert body is not None
        assert ".agentic-beacon/.legacy-migrated" not in body
        assert "sample-warehouse/" not in body
        assert content.count(".agentic-beacon/config.toml") == 1

    def test_tc2_legacy_header_all_managed_dropped(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text(
            "# Agentic Beacon\n"
            ".agentic-beacon/config.toml\n"
            ".agentic-beacon/artifacts/\n"
        )
        apply_managed_block(
            path, [".agentic-beacon/config.toml", ".agentic-beacon/artifacts/"]
        )
        content = path.read_text()
        assert "# Agentic Beacon" not in content
        assert content.count(".agentic-beacon/config.toml") == 1
        body = read_managed_block(path)
        assert body is not None

    def test_tc3_mixed_block_with_scattered_agent_dir(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text(
            "# Agentic Beacon\n.claude/agents/\nkeep-me/\n.opencode/agents/\n"
        )
        apply_managed_block(path, TIER_A_ENTRIES)
        content = path.read_text()
        assert "# Agentic Beacon" not in content
        assert "keep-me/" in content
        assert content.count(".claude/agents/") == 1
        assert content.count(".opencode/agents/") == 1

    def test_tc4_migration_idempotent(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text(
            "# Agentic Beacon\n.agentic-beacon/config.toml\ncustom-entry/\n"
        )
        apply_managed_block(path, TIER_A_ENTRIES)
        first = path.read_bytes()
        apply_managed_block(path, TIER_A_ENTRIES)
        second = path.read_bytes()
        assert first == second

    def test_tc5_substring_not_deduped(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text("# Agentic Beacon\n.agentic-beacon/config.toml.extra\n")
        apply_managed_block(path, TIER_A_ENTRIES)
        content = path.read_text()
        assert ".agentic-beacon/config.toml.extra" in content

    def test_tc6_real_scattered_fixture(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text(
            "# Editor and IDE\n"
            ".vscode/\n"
            "\n"
            "# Agentic Beacon\n"
            ".claude/scheduled_tasks.lock\n"
            "\n"
            ".agentic-beacon/config.toml\n"
            ".agentic-beacon/artifacts/\n"
            ".agentic-beacon/warehouse-catalog.md\n"
            ".agentic-beacon/pending.yaml\n"
            ".agentic-beacon/.legacy-migrated\n"
            "\n"
            "# Local sample-warehouse checkout (developer convenience; never a submodule)\n"
            "sample-warehouse/\n"
            ".claude/agents/\n"
            ".opencode/agents/\n"
        )
        apply_managed_block(path, TIER_A_ENTRIES)
        content = path.read_text()
        for entry in TIER_A_ENTRIES:
            assert content.splitlines().count(entry) == 1, (
                f"{entry} should appear exactly once"
            )
        assert ".claude/scheduled_tasks.lock" in content
        assert ".agentic-beacon/.legacy-migrated" in content
        assert "sample-warehouse/" in content
        assert ".vscode/" in content
        assert "# Editor and IDE" in content
        assert "Local sample-warehouse" in content
        apply_managed_block(path, TIER_A_ENTRIES)
        assert path.read_bytes() == content.encode("utf-8")


# ═════════════════════════════════════════════════════════════
# 1.4 read_managed_block & apply_all_gitignores
# ═════════════════════════════════════════════════════════════


class TestApplyAllGitignores:
    def test_tc1_no_tool_dirs_root_only(self, tmp_path):
        apply_all_gitignores(tmp_path)
        root = tmp_path / ".gitignore"
        assert root.exists()
        body = read_managed_block(root)
        assert body is not None
        assert set(body) == set(TIER_A_ENTRIES)
        assert not (tmp_path / ".claude" / ".gitignore").exists()
        assert not (tmp_path / ".opencode" / ".gitignore").exists()

    def test_tc2_claude_only(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        apply_all_gitignores(tmp_path)
        root = tmp_path / ".gitignore"
        assert root.exists()
        claude_gitignore = tmp_path / ".claude" / ".gitignore"
        assert claude_gitignore.exists()
        assert not (tmp_path / ".opencode" / ".gitignore").exists()
        claude_body = read_managed_block(claude_gitignore)
        assert claude_body == TIER_B_CLAUDE_ENTRIES

    def test_tc3_both_tool_dirs(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".opencode").mkdir()
        apply_all_gitignores(tmp_path)
        assert (tmp_path / ".claude" / ".gitignore").exists()
        assert (tmp_path / ".opencode" / ".gitignore").exists()
        oc_body = read_managed_block(tmp_path / ".opencode" / ".gitignore")
        assert oc_body == TIER_B_OPENCODE_ENTRIES

    def test_tc4_read_managed_block_no_markers(self, tmp_path):
        path = tmp_path / ".gitignore"
        path.write_text("some-line\n")
        assert read_managed_block(path) is None

    def test_tc4_read_managed_block_nonexistent(self, tmp_path):
        path = tmp_path / ".gitignore"
        assert read_managed_block(path) is None

    def test_tc4_read_returns_entries(self, tmp_path):
        path = tmp_path / ".gitignore"
        apply_managed_block(path, TIER_B_CLAUDE_ENTRIES)
        body = read_managed_block(path)
        assert body == TIER_B_CLAUDE_ENTRIES

    def test_returns_true_on_fresh_write_false_on_idempotent(self, tmp_path):
        assert apply_all_gitignores(tmp_path) is True
        assert apply_all_gitignores(tmp_path) is False


# ═════════════════════════════════════════════════════════════
# 1.5 diff_gitignores
# ═════════════════════════════════════════════════════════════


class TestDiffGitignores:
    def test_tc1_healthy_project(self, tmp_path):
        apply_all_gitignores(tmp_path)
        drifts = diff_gitignores(tmp_path)
        assert drifts == []

    def test_tc2_tier_b_present_tier_a_absent(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        root = tmp_path / ".gitignore"
        root.write_text("# user content\n")
        apply_managed_block(
            tmp_path / ".opencode" / ".gitignore", TIER_B_OPENCODE_ENTRIES
        )
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tier_a_missing" in kinds

    def test_tc3_tier_a_incomplete(self, tmp_path):
        subset = TIER_A_ENTRIES[:-1]
        apply_managed_block(tmp_path / ".gitignore", subset)
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tier_a_incomplete" in kinds

    def test_tc4_tier_b_missing_when_dir_exists(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        apply_managed_block(tmp_path / ".gitignore", TIER_A_ENTRIES)
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tier_b_missing" in kinds

    def test_tc5_tracked_set_ignored(self, tmp_path):
        _git_init(tmp_path)
        path = tmp_path / ".gitignore"
        path.write_text("beacon.yaml\n")
        apply_managed_block(path, TIER_A_ENTRIES)
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tracked_set_ignored" in kinds

    def test_tc6_read_only_no_writes(self, tmp_path):
        apply_all_gitignores(tmp_path)
        gitignore = tmp_path / ".gitignore"
        mtime_before = gitignore.stat().st_mtime
        diff_gitignores(tmp_path)
        mtime_after = gitignore.stat().st_mtime
        assert mtime_after == mtime_before

    def test_tier_a_missing_while_tier_b_present(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        (tmp_path / ".opencode" / ".gitignore").write_text(
            f"{MANAGED_BLOCK_BEGIN}\nskills/\n{MANAGED_BLOCK_END}\n"
        )
        drifts = diff_gitignores(tmp_path)
        kinds = {d.kind for d in drifts}
        assert "tier_a_missing" in kinds

    # ── FIX C: tracked-set detection with git check-ignore ──

    def test_glob_prefix_pattern_detected(self, tmp_path):
        """A directory glob pattern that would ignore a tracked-on-purpose file is detected."""
        _git_init(tmp_path)
        root = tmp_path / ".gitignore"
        root.write_text(".agentic-beacon/\n")
        drifts = diff_gitignores(tmp_path)
        tracked = [d for d in drifts if d.kind == "tracked_set_ignored"]
        assert any(".agentic-beacon/beacon.yaml" in d.message for d in tracked), (
            f"Expected tracked_set_ignored drift for beacon.yaml, got: {[d.message for d in tracked]}"
        )

    def test_healthy_project_zero_tracked_drift(self, tmp_path):
        """A properly-configured project with managed blocks must have zero tracked-set drift."""
        _git_init(tmp_path)
        apply_all_gitignores(tmp_path)
        drifts = diff_gitignores(tmp_path)
        assert len(drifts) == 0, (
            f"Expected zero drifts in healthy project, got: {[d.message for d in drifts]}"
        )

    # ── FIX G: order-sensitive comparison, extra/reordered detection ──

    def test_extra_line_in_managed_block_detected(self, tmp_path):
        """A managed block with an extra obsolete line reports tier_a_incomplete."""
        entries = TIER_A_ENTRIES + [".deprecated/"]
        apply_managed_block(tmp_path / ".gitignore", entries)
        drifts = diff_gitignores(tmp_path)
        incomplete = [d for d in drifts if d.kind == "tier_a_incomplete"]
        assert len(incomplete) == 1
        assert "Extra" in incomplete[0].detail

    def test_reordered_entries_detected(self, tmp_path):
        """Canonical entries in different order report drift."""
        entries = list(reversed(TIER_A_ENTRIES))
        apply_managed_block(tmp_path / ".gitignore", entries)
        drifts = diff_gitignores(tmp_path)
        incomplete = [d for d in drifts if d.kind == "tier_a_incomplete"]
        assert len(incomplete) == 1
        assert "reordered" in incomplete[0].detail

    def test_extra_line_healed_by_apply(self, tmp_path):
        """apply_all_gitignores repairs extra-line drift, then re-run is clean."""
        entries = TIER_A_ENTRIES + [".deprecated/"]
        apply_managed_block(tmp_path / ".gitignore", entries)
        assert diff_gitignores(tmp_path)
        apply_all_gitignores(tmp_path)
        assert diff_gitignores(tmp_path) == []

    def test_reorder_healed_by_apply(self, tmp_path):
        """apply_all_gitignores repairs reorder drift, then re-run is clean."""
        apply_managed_block(tmp_path / ".gitignore", list(reversed(TIER_A_ENTRIES)))
        assert diff_gitignores(tmp_path)
        apply_all_gitignores(tmp_path)
        assert diff_gitignores(tmp_path) == []

    def test_missing_entry_still_detected(self, tmp_path):
        """Subset entries still report tier_a_incomplete."""
        subset = TIER_A_ENTRIES[:-1]
        apply_managed_block(tmp_path / ".gitignore", subset)
        drifts = diff_gitignores(tmp_path)
        incomplete = [d for d in drifts if d.kind == "tier_a_incomplete"]
        assert len(incomplete) == 1
        assert "Missing" in incomplete[0].detail

    def test_healthy_still_clean(self, tmp_path):
        """Fully populated managed block reports zero drift."""
        apply_all_gitignores(tmp_path)
        assert diff_gitignores(tmp_path) == []

    def test_tracked_file_shows_drift_with_no_index(self, tmp_path):
        """ALREADY-TRACKED files ignored by .gitignore are detected with --no-index.

        Without --no-index, git check-ignore silently exits 1 for tracked
        files even when a .gitignore pattern matches them.
        """
        _git_init(tmp_path)
        beacon_dir = tmp_path / ".agentic-beacon"
        beacon_dir.mkdir()
        beacon_yaml = beacon_dir / "beacon.yaml"
        beacon_yaml.write_text("")
        root_gitignore = tmp_path / ".gitignore"
        root_gitignore.write_text(".agentic-beacon/\n")
        subprocess.run(
            ["git", "add", "-f", str(beacon_yaml), str(root_gitignore)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        drifts = diff_gitignores(tmp_path)
        tracked = [d for d in drifts if d.kind == "tracked_set_ignored"]
        assert any(".agentic-beacon/beacon.yaml" in d.message for d in tracked), (
            f"Expected tracked_set_ignored drift for beacon.yaml, got: {[d.message for d in tracked]}"
        )


# ═════════════════════════════════════════════════════════════
# 4.3 Tier B regression lock
# ═════════════════════════════════════════════════════════════


class TestTierBRegressionLock:
    def test_claude_entries_match_prior(self):
        assert TIER_B_CLAUDE_ENTRIES == [
            "skills/",
            "scheduled_tasks.lock",
            "worktrees/",
        ]

    def test_opencode_entries_match_prior(self):
        assert TIER_B_OPENCODE_ENTRIES == [
            "skills/",
            "command/",
            "bun.lock",
            "package.json",
            "package-lock.json",
            "node_modules/",
        ]

    def test_tier_b_gated_by_dir(self, tmp_path):
        apply_all_gitignores(tmp_path)
        assert not (tmp_path / ".claude" / ".gitignore").exists()
        assert not (tmp_path / ".opencode" / ".gitignore").exists()


# ═════════════════════════════════════════════════════════════
# 4.1 Unconditional Tier A (no tool dirs, no agents)
# ═════════════════════════════════════════════════════════════


class TestUnconditionalTierA:
    def test_all_10_entries_present_without_tool_dirs(self, tmp_path):
        apply_all_gitignores(tmp_path)
        body = read_managed_block(tmp_path / ".gitignore")
        assert body is not None
        assert len(body) == len(TIER_A_ENTRIES)
        for entry in TIER_A_ENTRIES:
            assert entry in body

    def test_agent_dirs_in_block_no_declared_agents(self, tmp_path):
        apply_all_gitignores(tmp_path)
        body = read_managed_block(tmp_path / ".gitignore")
        assert body is not None
        assert ".claude/agents/" in body
        assert ".opencode/agents/" in body
