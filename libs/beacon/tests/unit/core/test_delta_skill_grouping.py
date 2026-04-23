"""Unit tests for skill grouping in delta view."""

from beacon.domains.contribution.delta_view import (
    partition_tracked_diffs,
    render_skill_group,
    skill_entries,
)
from beacon.domains.distribution.delta import ComparisonResult, DeltaStatus


def make_result(
    path: str, status: DeltaStatus, agent_statuses: dict | None = None
) -> ComparisonResult:
    """Helper to create a ComparisonResult."""
    return ComparisonResult(
        path=path,
        status=status,
        agent_statuses=agent_statuses or {},
    )


class TestSkillEntries:
    def test_empty_list(self):
        assert skill_entries([]) == []

    def test_no_skills(self):
        results = [
            make_result("knowledge/python.md", DeltaStatus.MODIFIED),
            make_result("contexts/team.md", DeltaStatus.ADDED),
        ]
        assert skill_entries(results) == []

    def test_single_skill(self):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        assert skill_entries(results) == ["skills/my-skill"]

    def test_multiple_files_same_skill(self):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result(
                "skills/my-skill/script.py",
                DeltaStatus.ADDED,
                {"opencode": DeltaStatus.ADDED},
            ),
        ]
        assert skill_entries(results) == ["skills/my-skill"]

    def test_multiple_skills(self):
        results = [
            make_result(
                "skills/skill-a/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result(
                "skills/skill-b/SKILL.md",
                DeltaStatus.ADDED,
                {"opencode": DeltaStatus.ADDED},
            ),
        ]
        assert skill_entries(results) == ["skills/skill-a", "skills/skill-b"]

    def test_skill_with_nested_dir(self):
        results = [
            make_result(
                "skills/my-skill/subdir/file.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        assert skill_entries(results) == ["skills/my-skill"]

    def test_non_skill_results_ignored(self):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result("knowledge/python.md", DeltaStatus.MODIFIED),
        ]
        assert skill_entries(results) == ["skills/my-skill"]


class TestPartitionTrackedDiffs:
    def test_skill_results_grouped(self):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result(
                "skills/my-skill/script.py",
                DeltaStatus.ADDED,
                {"opencode": DeltaStatus.ADDED},
            ),
        ]
        node_groups, skill_groups, standalone = partition_tracked_diffs(results, [])
        assert node_groups == {}
        assert skill_groups == {"skills/my-skill": results}
        assert standalone == []

    def test_knowledge_node_grouped(self):
        results = [
            make_result("knowledge/python/decisions/a.md", DeltaStatus.MODIFIED),
            make_result("knowledge/python/decisions/b.md", DeltaStatus.ADDED),
        ]
        node_groups, skill_groups, standalone = partition_tracked_diffs(
            results, ["knowledge/python"]
        )
        assert node_groups == {"knowledge/python": results}
        assert skill_groups == {}
        assert standalone == []

    def test_standalone_results(self):
        results = [
            make_result("contexts/team.md", DeltaStatus.MODIFIED),
        ]
        node_groups, skill_groups, standalone = partition_tracked_diffs(results, [])
        assert node_groups == {}
        assert skill_groups == {}
        assert standalone == results

    def test_mixed_groups(self):
        skill_results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        node_results = [
            make_result("knowledge/python/decisions/a.md", DeltaStatus.MODIFIED),
        ]
        standalone_results = [
            make_result("contexts/team.md", DeltaStatus.MODIFIED),
        ]
        results = skill_results + node_results + standalone_results
        node_groups, skill_groups, standalone = partition_tracked_diffs(
            results, ["knowledge/python"]
        )
        assert node_groups == {"knowledge/python": node_results}
        assert skill_groups == {"skills/my-skill": skill_results}
        assert standalone == standalone_results

    def test_skills_checked_before_nodes(self):
        """Skills take priority if a path happens to match both patterns."""
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        # Even if someone accidentally lists "skills" as a node entry
        node_groups, skill_groups, standalone = partition_tracked_diffs(
            results, ["skills"]
        )
        assert skill_groups == {"skills/my-skill": results}
        assert node_groups == {}

    def test_empty_input(self):
        node_groups, skill_groups, standalone = partition_tracked_diffs([], [])
        assert node_groups == {}
        assert skill_groups == {}
        assert standalone == []


class TestRenderSkillGroup:
    def test_renders_header_and_badge(self, capsys):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {DeltaStatus.MODIFIED: "[yellow]modified[/yellow]"},
            {
                DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
                DeltaStatus.IDENTICAL: "[dim]synced[/dim]",
            },
            ["opencode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        assert "skills/my-skill/" in output
        assert "1 modified" in output
        assert "SKILL.md" in output
        assert "opencode" in output

    def test_renders_multiple_files(self, capsys):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result(
                "skills/my-skill/script.py",
                DeltaStatus.ADDED,
                {"opencode": DeltaStatus.ADDED},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {
                DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
                DeltaStatus.ADDED: "[green]added[/green]",
            },
            {
                DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
                DeltaStatus.ADDED: "[green]added[/green]",
                DeltaStatus.IDENTICAL: "[dim]synced[/dim]",
            },
            ["opencode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        assert "SKILL.md" in output
        assert "script.py" in output
        assert "modified" in output
        assert "added" in output

    def test_renders_multiple_agents(self, capsys):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED, "claudecode": DeltaStatus.IDENTICAL},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {DeltaStatus.MODIFIED: "[yellow]modified[/yellow]"},
            {
                DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
                DeltaStatus.IDENTICAL: "[dim]synced[/dim]",
            },
            ["opencode", "claudecode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        assert "opencode" in output
        assert "claudecode" in output
        assert "modified" in output
        assert "synced" in output

    def test_no_badge_when_all_identical(self, capsys):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.IDENTICAL,
                {"opencode": DeltaStatus.IDENTICAL},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {DeltaStatus.IDENTICAL: "[dim]identical[/dim]"},
            {DeltaStatus.IDENTICAL: "[dim]synced[/dim]"},
            ["opencode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        assert "skills/my-skill/" in output
        # No status counts in badge since all are identical
        assert "modified" not in output
        assert "added" not in output
        assert "missing" not in output

    def test_stale_status_in_badge(self, capsys):
        results = [
            make_result(
                "skills/my-skill/SKILL.md",
                DeltaStatus.STALE,
                {"opencode": DeltaStatus.STALE},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]"},
            {DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]"},
            ["opencode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        assert "1 stale" in output

    def test_files_sorted_alphabetically(self, capsys):
        results = [
            make_result(
                "skills/my-skill/zebra.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
            make_result(
                "skills/my-skill/alpha.md",
                DeltaStatus.MODIFIED,
                {"opencode": DeltaStatus.MODIFIED},
            ),
        ]
        render_skill_group(
            "skills/my-skill",
            results,
            {DeltaStatus.MODIFIED: "[yellow]modified[/yellow]"},
            {DeltaStatus.MODIFIED: "[yellow]modified[/yellow]"},
            ["opencode"],
        )
        captured = capsys.readouterr()
        output = captured.out
        alpha_pos = output.find("alpha.md")
        zebra_pos = output.find("zebra.md")
        assert alpha_pos < zebra_pos
        assert alpha_pos != -1
        assert zebra_pos != -1
