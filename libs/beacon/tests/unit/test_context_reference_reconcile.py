"""Unit tests for the context-reference reconciler (AB-96).

Covers tasks 1.1-1.5, 4.1-4.2 from
openspec/changes/reconcile-context-references/tasks.md.
"""

import json
from pathlib import Path

import pytest
from beacon.domains.setup.wiring import (
    ReferenceReconcileResult,
    _reconcile_agents_md,
    _reconcile_opencode_json,
    desired_context_refs,
    reconcile_context_references,
    unwire_pruned_artifacts,
)

# ---------------------------------------------------------------------------
# Task 1.1: desired_context_refs
# ---------------------------------------------------------------------------


class TestDesiredContextRefs:
    def test_tc1_two_contexts_sorted(self):
        """TC1: two context names -> two sorted .agentic-beacon/artifacts/contexts/<name>.md paths."""
        result = desired_context_refs({"python-standards", "beacon-ops"})
        assert result == [
            ".agentic-beacon/artifacts/contexts/beacon-ops.md",
            ".agentic-beacon/artifacts/contexts/python-standards.md",
        ]

    def test_tc2_empty_set(self):
        """TC2: empty effective set -> empty list."""
        assert desired_context_refs(set()) == []

    def test_tc3_names_with_dots_hyphens(self):
        """TC3: names already containing dots/hyphens map to <name>.md unchanged."""
        result = desired_context_refs({"my-ctx.v2", "hello-world"})
        assert result == [
            ".agentic-beacon/artifacts/contexts/hello-world.md",
            ".agentic-beacon/artifacts/contexts/my-ctx.v2.md",
        ]

    def test_tc4_nested_context_subpath(self):
        """Nested context with a subpath (slashes preserved)."""
        result = desired_context_refs({"teams/backend/onboarding"})
        assert result == [
            ".agentic-beacon/artifacts/contexts/teams/backend/onboarding.md",
        ]


# ---------------------------------------------------------------------------
# Task 1.2: _reconcile_opencode_json
# ---------------------------------------------------------------------------


class TestReconcileOpencodeJson:
    def _make_json(self, project_root: Path, data: dict) -> Path:
        p = project_root / "opencode.json"
        p.write_text(json.dumps(data, indent=2) + "\n")
        return p

    def test_tc1_remove_departed_owned_ref(self, tmp_path):
        """TC1: owned ref not in desired -> removed; returned removed lists it."""
        self._make_json(
            tmp_path,
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [
                    ".agentic-beacon/artifacts/contexts/linear-ops.md",
                    "docs/house-style.md",
                ],
            },
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = _reconcile_opencode_json(tmp_path, desired)
        assert result.added == [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        assert result.removed == [".agentic-beacon/artifacts/contexts/linear-ops.md"]

        data = json.loads((tmp_path / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in data["instructions"]
        )
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in data["instructions"]
        assert "docs/house-style.md" in data["instructions"]
        assert data["$schema"] == "https://opencode.ai/config.json"

    def test_tc2_add_missing_desired_ref(self, tmp_path):
        """TC2: desired ref missing from instructions -> appended."""
        self._make_json(
            tmp_path,
            {"$schema": "https://opencode.ai/config.json", "instructions": []},
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_opencode_json(tmp_path, desired)
        assert result.added == [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        assert result.removed == []

        data = json.loads((tmp_path / "opencode.json").read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/beacon-ops.md" in data["instructions"]
        )

    def test_tc3_preserves_schema_and_user_entries(self, tmp_path):
        """TC3: $schema + user entry preserved, order stable."""
        self._make_json(
            tmp_path,
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [
                    ".agentic-beacon/artifacts/contexts/linear-ops.md",
                    "docs/house-style.md",
                    ".agentic-beacon/artifacts/contexts/cicd-flow.md",
                ],
            },
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = _reconcile_opencode_json(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/cicd-flow.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in result.added

        data = json.loads((tmp_path / "opencode.json").read_text())
        assert data["instructions"] == [
            "docs/house-style.md",
            ".agentic-beacon/artifacts/contexts/plane-ops.md",
        ]

    def test_tc4_idempotent_no_write(self, tmp_path):
        """TC4: instructions already match -> file bytes unchanged."""
        content = {
            "$schema": "https://opencode.ai/config.json",
            "instructions": [
                ".agentic-beacon/artifacts/contexts/beacon-ops.md",
            ],
        }
        p = self._make_json(tmp_path, content)
        mtime_before = p.stat().st_mtime
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_opencode_json(tmp_path, desired)
        assert result.added == []
        assert result.removed == []
        assert p.stat().st_mtime == mtime_before

    def test_tc5_empty_desired_clears_owned(self, tmp_path):
        """TC5: empty desired set -> all owned refs removed, non-owned preserved."""
        self._make_json(
            tmp_path,
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [
                    ".agentic-beacon/artifacts/contexts/linear-ops.md",
                    "docs/house-style.md",
                    ".agentic-beacon/artifacts/contexts/cicd-flow.md",
                ],
            },
        )
        result = _reconcile_opencode_json(tmp_path, [])
        assert len(result.removed) == 2
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/cicd-flow.md" in result.removed

        data = json.loads((tmp_path / "opencode.json").read_text())
        assert data["instructions"] == ["docs/house-style.md"]

    def test_tc6_serialization_shape(self, tmp_path):
        """TC6: output re-serialized with 2-space indent and single trailing newline."""
        self._make_json(
            tmp_path,
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [
                    ".agentic-beacon/artifacts/contexts/linear-ops.md",
                ],
            },
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        _reconcile_opencode_json(tmp_path, desired)
        text = (tmp_path / "opencode.json").read_text()
        assert text.endswith("\n")
        # Verify 2-space indent by re-parsing
        data = json.loads(text)
        assert data["instructions"] == [
            ".agentic-beacon/artifacts/contexts/beacon-ops.md"
        ]

    def test_tc7_no_file_noop(self, tmp_path):
        """TC7: no opencode.json present -> no-op, empty result."""
        result = _reconcile_opencode_json(
            tmp_path, [".agentic-beacon/artifacts/contexts/x.md"]
        )
        assert result.added == []
        assert result.removed == []


# ---------------------------------------------------------------------------
# Task 1.3: _reconcile_agents_md (pure reconcile of the root AGENTS.md)
# ---------------------------------------------------------------------------


class TestReconcileAgentsMd:
    def test_tc1_remove_departed_owned_ref(self, tmp_path):
        """TC1: owned @-include not in desired -> line removed; other lines untouched."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Project\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
            "@docs/house-style.md\n"
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = _reconcile_agents_md(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in result.added

        content = agents.read_text()
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in content
        assert "# Project" in content
        assert "@docs/house-style.md" in content

    def test_tc2_add_missing_desired_ref(self, tmp_path):
        """TC2: desired ref absent -> appended."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# Project\n")
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_agents_md(tmp_path, desired)
        assert result.added == [".agentic-beacon/artifacts/contexts/beacon-ops.md"]

        content = agents.read_text()
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content
        assert "# Project" in content

    def test_tc3_preserves_non_artifact_includes(self, tmp_path):
        """TC3: only artifact includes change, others stay in place."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Project\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
            "@docs/house-style.md\n"
            "@.agentic-beacon/artifacts/contexts/cicd-flow.md\n"
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_agents_md(tmp_path, desired)
        assert len(result.removed) == 2

        content = agents.read_text()
        assert "# Project" in content
        assert "@docs/house-style.md" in content
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/cicd-flow.md" not in content

    def test_tc4_idempotent_no_write(self, tmp_path):
        """TC4: already-matching file -> bytes unchanged."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text("@.agentic-beacon/artifacts/contexts/beacon-ops.md\n")
        mtime_before = agents.stat().st_mtime
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_agents_md(tmp_path, desired)
        assert result.added == []
        assert result.removed == []
        assert agents.stat().st_mtime == mtime_before

    def test_tc5_empty_desired_clears_owned(self, tmp_path):
        """TC5: empty desired set -> all owned includes removed."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Project\n@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )
        result = _reconcile_agents_md(tmp_path, [])
        assert len(result.removed) == 1

        content = agents.read_text()
        assert "# Project" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content

    def test_tc6_missing_agents_md_and_no_claude_md_is_noop(self, tmp_path):
        """TC6: no AGENTS.md and no CLAUDE.md -> nothing created, empty result."""
        result = _reconcile_agents_md(
            tmp_path, [".agentic-beacon/artifacts/contexts/x.md"]
        )
        assert result.added == []
        assert result.removed == []
        assert not (tmp_path / "AGENTS.md").exists()

    def test_handles_missing_trailing_newline(self, tmp_path):
        """Handle file without trailing newline."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# Project")
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_agents_md(tmp_path, desired)
        assert len(result.added) == 1
        content = agents.read_text()
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content

    def test_intersection_present_and_desired_preserved(self, tmp_path):
        """BUG REGRESSION: refs in owned ∩ desired must NOT be dropped.

        The bug: old code stripped all owned lines then re-appended only
        ``added`` (desired − owned), so the intersection was silently wiped.
        """
        agents = tmp_path / "AGENTS.md"
        # python-standards is both currently owned AND desired (intersection).
        # linear-ops is owned but NOT desired (should be removed).
        agents.write_text(
            "# Project\n"
            "@.agentic-beacon/artifacts/contexts/python-standards.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )
        desired = [
            ".agentic-beacon/artifacts/contexts/python-standards.md",
            ".agentic-beacon/artifacts/contexts/beacon-ops.md",
        ]
        result = _reconcile_agents_md(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/beacon-ops.md" in result.added

        content = agents.read_text()
        assert "@.agentic-beacon/artifacts/contexts/python-standards.md" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content
        assert "# Project" in content

    def test_idempotent_after_partial_drift(self, tmp_path):
        """After reconciling drift, a second run is a no-op (byte-identical output)."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Project\n"
            "@.agentic-beacon/artifacts/contexts/python-standards.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )
        desired = [
            ".agentic-beacon/artifacts/contexts/python-standards.md",
            ".agentic-beacon/artifacts/contexts/beacon-ops.md",
        ]
        _reconcile_agents_md(tmp_path, desired)
        content_after_run1 = agents.read_bytes()
        mtime_after_run1 = agents.stat().st_mtime

        result2 = _reconcile_agents_md(tmp_path, desired)
        assert result2.added == []
        assert result2.removed == []
        assert agents.read_bytes() == content_after_run1
        assert agents.stat().st_mtime == mtime_after_run1

    def test_live_shape_regression(self, tmp_path):
        """Live-shape regression: 7 owned refs (incl. departed linear-ops) → 5 desired remain.

        Mirrors the exact repo condition that motivated AB-96:
        linear-ops was renamed to plane-ops; cicd-flow was de-adopted.
        """
        owned_names = [
            "python-standards",
            "openspec-workflow",
            "cicd-flow",
            "agent-practices",
            "linear-ops",
            "beacon-ops",
            "plane-ops",
        ]
        desired_names = [
            "python-standards",
            "openspec-workflow",
            "agent-practices",
            "beacon-ops",
            "plane-ops",
        ]
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Project\n\n"
            + "\n\n".join(
                f"@.agentic-beacon/artifacts/contexts/{n}.md" for n in owned_names
            )
            + "\n"
        )
        desired = desired_context_refs(set(desired_names))
        result = _reconcile_agents_md(tmp_path, desired)

        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/cicd-flow.md" in result.removed

        content = agents.read_text()
        assert "# Project" in content
        for name in desired_names:
            assert f"@.agentic-beacon/artifacts/contexts/{name}.md" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/cicd-flow.md" not in content

        # Second run must be idempotent
        result2 = _reconcile_agents_md(tmp_path, desired)
        assert result2.added == []
        assert result2.removed == []


# ---------------------------------------------------------------------------
# Task 1.3: CLAUDE.md migration into AGENTS.md
# ---------------------------------------------------------------------------

OWNED_LINOPS = "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
OWNED_A = ".agentic-beacon/artifacts/contexts/a.md"
DESIRED_PLANE = [".agentic-beacon/artifacts/contexts/plane-ops.md"]


class TestClaudeMdMigration:
    def test_thin_claude_md_deleted_even_without_agents_md(self, tmp_path):
        """A thin CLAUDE.md is deleted, and reported as deleted, when AGENTS.md is missing."""
        (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n")

        result = _reconcile_agents_md(tmp_path, [])

        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / "AGENTS.md").exists()
        assert result.claude_md_deleted == ("CLAUDE.md",)

    def test_tc1_thin_claude_md_deleted_imports_land_in_agents_md(self, tmp_path):
        """TC1: thin CLAUDE.md is deleted; its owned import is appended to AGENTS.md."""
        (tmp_path / "AGENTS.md").write_text("# Project\n")
        (tmp_path / "CLAUDE.md").write_text(f"@AGENTS.md\n@{OWNED_A}\n")

        result = _reconcile_agents_md(tmp_path, [OWNED_A])

        assert not (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "AGENTS.md").read_text().endswith(f"@{OWNED_A}\n")
        assert result.claude_md_deleted == ("CLAUDE.md",)
        assert result.claude_md_left == ()

    def test_tc2_html_comments_and_dot_slash_import_are_trivial(self, tmp_path):
        """TC2: HTML comments, blanks and @./AGENTS.md do not block deletion."""
        (tmp_path / "AGENTS.md").write_text("")
        (tmp_path / "CLAUDE.md").write_text(
            f"<!-- note -->\n\n@./AGENTS.md\n<!--\nmulti\n-->\n{OWNED_LINOPS}"
        )

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        assert not (tmp_path / "CLAUDE.md").exists()
        assert result.claude_md_deleted == ("CLAUDE.md",)
        assert (
            "@.agentic-beacon/artifacts/contexts/plane-ops.md"
            in (tmp_path / "AGENTS.md").read_text()
        )

    def test_tc3_claude_md_with_heading_is_kept_stripped_and_reported(self, tmp_path):
        """TC3: a CLAUDE.md with other content keeps its lines; owned line stripped."""
        (tmp_path / "AGENTS.md").write_text("")
        (tmp_path / "CLAUDE.md").write_text(f"# Title\n@AGENTS.md\n{OWNED_LINOPS}")

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        content = (tmp_path / "CLAUDE.md").read_text()
        assert content == "# Title\n@AGENTS.md\n"
        assert result.claude_md_left == ("CLAUDE.md",)
        assert result.claude_md_deleted == ()

    def test_tc4_dot_claude_claude_md_migrated(self, tmp_path):
        """TC4: .claude/CLAUDE.md holding only owned lines and @AGENTS.md is deleted."""
        (tmp_path / "AGENTS.md").write_text("")
        dot_claude = tmp_path / ".claude"
        dot_claude.mkdir()
        (dot_claude / "CLAUDE.md").write_text(f"@AGENTS.md\n{OWNED_LINOPS}")

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        assert not (dot_claude / "CLAUDE.md").exists()
        assert result.claude_md_deleted == (".claude/CLAUDE.md",)
        assert (
            "@.agentic-beacon/artifacts/contexts/plane-ops.md"
            in (tmp_path / "AGENTS.md").read_text()
        )

    def test_tc5_missing_agents_md_created_when_claude_md_held_owned_lines(
        self, tmp_path
    ):
        """TC5: no AGENTS.md, CLAUDE.md held an owned line -> AGENTS.md created."""
        (tmp_path / "CLAUDE.md").write_text(OWNED_LINOPS)

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        assert (tmp_path / "AGENTS.md").read_text() == (
            "@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
        )
        assert result.added == DESIRED_PLANE
        assert result.removed == [".agentic-beacon/artifacts/contexts/linear-ops.md"]
        assert result.claude_md_deleted == ("CLAUDE.md",)

    def test_tc7_claude_md_symlink_to_agents_md_untouched(self, tmp_path):
        """TC7: CLAUDE.md symlinked to AGENTS.md is skipped; AGENTS.md reconciled once."""
        agents = tmp_path / "AGENTS.md"
        agents.write_text(OWNED_LINOPS)
        (tmp_path / "CLAUDE.md").symlink_to("AGENTS.md")

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        assert (tmp_path / "CLAUDE.md").is_symlink()
        assert (
            agents.read_text() == "@.agentic-beacon/artifacts/contexts/plane-ops.md\n"
        )
        assert result.claude_md_deleted == ()
        assert result.claude_md_left == ()

    def test_tc8_dry_run_reports_without_writing(self, tmp_path):
        """TC8: dry_run reports the migration; no file written or deleted."""
        (tmp_path / "AGENTS.md").write_text("# Project\n")
        (tmp_path / "CLAUDE.md").write_text(f"@AGENTS.md\n@{OWNED_A}\n")
        agents_before = (tmp_path / "AGENTS.md").read_bytes()
        claude_before = (tmp_path / "CLAUDE.md").read_bytes()

        result = _reconcile_agents_md(tmp_path, [OWNED_A], dry_run=True)

        assert (tmp_path / "CLAUDE.md").read_bytes() == claude_before
        assert (tmp_path / "AGENTS.md").read_bytes() == agents_before
        assert result.added == [OWNED_A]
        assert result.claude_md_deleted == ("CLAUDE.md",)

    def test_tc9_second_run_after_migration_is_noop(self, tmp_path):
        """TC9: after migration a second run changes nothing."""
        (tmp_path / "AGENTS.md").write_text("# Project\n")
        (tmp_path / "CLAUDE.md").write_text(f"@AGENTS.md\n@{OWNED_A}\n")
        _reconcile_agents_md(tmp_path, [OWNED_A])
        agents_after_first = (tmp_path / "AGENTS.md").read_bytes()

        result = _reconcile_agents_md(tmp_path, [OWNED_A])

        assert result == ReferenceReconcileResult(added=[], removed=[])
        assert (tmp_path / "AGENTS.md").read_bytes() == agents_after_first

    def test_tc10_claude_md_without_owned_lines_left_byte_identical(self, tmp_path):
        """TC10: CLAUDE.md with other content and no owned lines is left as-is."""
        (tmp_path / "AGENTS.md").write_text("")
        original = "# Team rules\n\nAlways run tests.\n"
        (tmp_path / "CLAUDE.md").write_text(original)

        result = _reconcile_agents_md(tmp_path, DESIRED_PLANE)

        assert (tmp_path / "CLAUDE.md").read_text() == original
        assert result.claude_md_left == ("CLAUDE.md",)

    @pytest.mark.parametrize(
        "content",
        ["@AGENTS.md\n", "<!-- only a comment -->\n\n", ""],
        ids=["agents-import", "comment-only", "empty"],
    )
    def test_thin_claude_md_without_owned_lines_deleted(self, tmp_path, content):
        """A thin CLAUDE.md with no owned lines is deleted (the delete test, D5)."""
        (tmp_path / "AGENTS.md").write_text("# Project\n")
        (tmp_path / "CLAUDE.md").write_text(content)

        result = _reconcile_agents_md(tmp_path, [])

        assert not (tmp_path / "CLAUDE.md").exists()
        assert result.claude_md_deleted == ("CLAUDE.md",)


# ---------------------------------------------------------------------------
# Task 1.4: reconcile_context_references
# ---------------------------------------------------------------------------


class TestReconcileContextReferences:
    def _setup_both(self, tmp_path, opencode_instructions, agents_lines):
        """Helper to set up opencode.json and AGENTS.md with given content."""
        if opencode_instructions is not None:
            p = tmp_path / "opencode.json"
            p.write_text(
                json.dumps(
                    {
                        "$schema": "https://opencode.ai/config.json",
                        "instructions": opencode_instructions,
                    },
                    indent=2,
                )
                + "\n"
            )
        if agents_lines is not None:
            (tmp_path / "AGENTS.md").write_text(agents_lines)

    def test_tc1_both_files_drift(self, tmp_path):
        """TC1: both files drift -> aggregated added/removed spans both."""
        self._setup_both(
            tmp_path,
            opencode_instructions=[
                ".agentic-beacon/artifacts/contexts/linear-ops.md",
                "docs/house-style.md",
            ],
            agents_lines=(
                "@AGENTS.md\n@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
            ),
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = reconcile_context_references(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in result.added

    def test_tc2_dry_run_no_writes(self, tmp_path):
        """TC2: dry_run=True -> delta computed but files unchanged."""
        self._setup_both(
            tmp_path,
            opencode_instructions=[
                ".agentic-beacon/artifacts/contexts/linear-ops.md",
            ],
            agents_lines="@.agentic-beacon/artifacts/contexts/linear-ops.md\n",
        )
        oc_before = (tmp_path / "opencode.json").read_bytes()
        cl_before = (tmp_path / "AGENTS.md").read_bytes()
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = reconcile_context_references(tmp_path, desired, dry_run=True)
        assert len(result.added) > 0 or len(result.removed) > 0
        assert (tmp_path / "opencode.json").read_bytes() == oc_before
        assert (tmp_path / "AGENTS.md").read_bytes() == cl_before

    def test_tc3_idempotent(self, tmp_path):
        """TC3: second call returns empty added/removed; byte-identical output."""
        self._setup_both(
            tmp_path,
            opencode_instructions=[
                ".agentic-beacon/artifacts/contexts/beacon-ops.md",
            ],
            agents_lines="@.agentic-beacon/artifacts/contexts/beacon-ops.md\n",
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result1 = reconcile_context_references(tmp_path, desired)
        # First run on already-matching files should be a no-op
        assert result1.added == []
        assert result1.removed == []
        result2 = reconcile_context_references(tmp_path, desired)
        assert result2.added == []
        assert result2.removed == []

    def test_tc4_only_one_file_exists(self, tmp_path):
        """TC4: only one of the two files exists -> other reconciler is silent no-op."""
        (tmp_path / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/linear-ops.md"
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = reconcile_context_references(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in result.added

    def test_tc5_carries_claude_md_migration_paths(self, tmp_path):
        """TC5: a thin CLAUDE.md migrated during reconcile is reported on the aggregate."""
        self._setup_both(
            tmp_path, opencode_instructions=None, agents_lines="# Project\n"
        )
        (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n")
        result = reconcile_context_references(tmp_path, [])
        assert result.claude_md_deleted == ("CLAUDE.md",)
        assert result.claude_md_left == ()
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_live_shape_regression_both_files(self, tmp_path):
        """Live-shape regression: 7 owned refs (incl. linear-ops) across both files → 6 desired.

        Verifies the critical bug fix: present-and-desired intersection refs
        must survive reconcile (not be silently wiped).
        """
        owned_names = [
            "python-standards",
            "openspec-workflow",
            "cicd-flow",
            "agent-practices",
            "linear-ops",
            "beacon-ops",
            "plane-ops",
        ]
        desired_names = {
            "python-standards",
            "openspec-workflow",
            "agent-practices",
            "beacon-ops",
            "plane-ops",
        }
        # Setup AGENTS.md with 7 owned refs
        (tmp_path / "AGENTS.md").write_text(
            "# Project\n\n"
            + "\n\n".join(
                f"@.agentic-beacon/artifacts/contexts/{n}.md" for n in owned_names
            )
            + "\n"
        )
        # Setup opencode.json with 7 owned refs
        (tmp_path / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        f".agentic-beacon/artifacts/contexts/{n}.md"
                        for n in owned_names
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        desired = desired_context_refs(desired_names)
        result = reconcile_context_references(tmp_path, desired)

        # linear-ops and cicd-flow should be removed
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/cicd-flow.md" in result.removed

        # All 5 desired should be present in AGENTS.md
        claude_content = (tmp_path / "AGENTS.md").read_text()
        for name in desired_names:
            assert f"@.agentic-beacon/artifacts/contexts/{name}.md" in claude_content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in claude_content
        assert "# Project" in claude_content

        # All 5 desired should be present in opencode.json
        oc_data = json.loads((tmp_path / "opencode.json").read_text())
        oc_instructions = oc_data["instructions"]
        for name in desired_names:
            assert f".agentic-beacon/artifacts/contexts/{name}.md" in oc_instructions
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" not in oc_instructions

        # Second run is idempotent
        result2 = reconcile_context_references(tmp_path, desired)
        assert result2.added == []
        assert result2.removed == []


# ---------------------------------------------------------------------------
# Task 1.5: unwire_pruned_artifacts context branch removed
# ---------------------------------------------------------------------------


class TestUnwirePrunedArtifactsContextBranch:
    def test_tc1_skill_prune_still_works(self, tmp_path):
        """TC1: unwire_pruned_artifacts on a pruned skill still removes skill dirs."""
        opencode_skill = tmp_path / ".opencode" / "skills" / "code-review"
        opencode_skill.mkdir(parents=True)
        (opencode_skill / "SKILL.md").write_text("review skill")
        claude_skill = tmp_path / ".claude" / "skills" / "code-review"
        claude_skill.mkdir(parents=True)
        (claude_skill / "SKILL.md").write_text("review skill")
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"

        unwire_pruned_artifacts(
            tmp_path,
            ["skills/code-review/SKILL.md"],
            artifacts_dir,
        )

        assert not opencode_skill.exists()
        assert not claude_skill.exists()

    def test_tc2_agent_prune_still_works(self, tmp_path):
        """TC2: unwire_pruned_artifacts on a pruned agent still removes agent symlinks."""
        agent_target = (
            tmp_path / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
        )
        agent_target.parent.mkdir(parents=True)
        agent_target.write_text("agent")
        cc_link = tmp_path / ".claude" / "agents" / "spec-planner.md"
        cc_link.parent.mkdir(parents=True)
        cc_link.symlink_to(agent_target)
        oc_link = tmp_path / ".opencode" / "agents" / "spec-planner.md"
        oc_link.parent.mkdir(parents=True)
        oc_link.symlink_to(agent_target)

        unwire_pruned_artifacts(
            tmp_path,
            ["agents/spec-planner.md"],
            tmp_path / ".agentic-beacon" / "artifacts",
        )

        assert not cc_link.exists()
        assert not oc_link.exists()

    def test_tc3_context_prune_is_noop(self, tmp_path):
        """TC3: unwire_pruned_artifacts on a pruned context is now a no-op (reconcile owns it)."""
        opencode_json = tmp_path / "opencode.json"
        opencode_json.write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/linear-ops.md"
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text("@.agentic-beacon/artifacts/contexts/linear-ops.md\n")

        unwire_pruned_artifacts(
            tmp_path,
            ["contexts/linear-ops.md"],
            tmp_path / ".agentic-beacon" / "artifacts",
        )

        # Context references should NOT be removed by prune unwire anymore
        data = json.loads(opencode_json.read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md" in data["instructions"]
        )
        assert (
            "@.agentic-beacon/artifacts/contexts/linear-ops.md" in agents_md.read_text()
        )


# ---------------------------------------------------------------------------
# Task 4.2: Dangling / warehouse-rename case
# ---------------------------------------------------------------------------


class TestDanglingWarehouseRename:
    def test_tc1_dangling_reference_removed(self, tmp_path):
        """An owned reference not in the effective set (file gone) is removed from both files."""
        opencode_json = tmp_path / "opencode.json"
        opencode_json.write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "instructions": [
                        ".agentic-beacon/artifacts/contexts/linear-ops.md",
                        "docs/house-style.md",
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text(
            "# Project\n@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )

        # linear-ops not in desired set (renamed to plane-ops)
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = reconcile_context_references(tmp_path, desired)

        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        data = json.loads(opencode_json.read_text())
        assert (
            ".agentic-beacon/artifacts/contexts/linear-ops.md"
            not in data["instructions"]
        )
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in data["instructions"]
        assert (
            "@.agentic-beacon/artifacts/contexts/linear-ops.md"
            not in agents_md.read_text()
        )
        assert (
            "@.agentic-beacon/artifacts/contexts/plane-ops.md" in agents_md.read_text()
        )


# ---------------------------------------------------------------------------
# Test ReferenceReconcileResult shape
# ---------------------------------------------------------------------------


class TestReferenceReconcileResult:
    def test_empty_result(self):
        r = ReferenceReconcileResult(added=[], removed=[])
        assert r.added == []
        assert r.removed == []
        assert bool(r) is False

    def test_non_empty_result(self):
        r = ReferenceReconcileResult(added=["a.md"], removed=["b.md"])
        assert bool(r) is True

    def test_migration_fields_default_empty_and_not_truthy(self):
        r = ReferenceReconcileResult(added=[], removed=[])
        assert r.claude_md_deleted == ()
        assert r.claude_md_left == ()
        assert bool(ReferenceReconcileResult([], [], ("CLAUDE.md",), ())) is False
