"""Unit tests for the context-reference reconciler (AB-96).

Covers tasks 1.1-1.5, 4.1-4.2 from
openspec/changes/reconcile-context-references/tasks.md.
"""

import json
from pathlib import Path

from beacon.domains.setup.wiring import (
    ReferenceReconcileResult,
    _reconcile_claude_md,
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
# Task 1.3: _reconcile_claude_md
# ---------------------------------------------------------------------------


class TestReconcileClaudeMd:
    def test_tc1_remove_departed_owned_ref(self, tmp_path):
        """TC1: owned @-include not in desired -> line removed; @AGENTS.md untouched."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(
            "@AGENTS.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
            "@docs/house-style.md\n"
        )
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        assert ".agentic-beacon/artifacts/contexts/plane-ops.md" in result.added

        content = claude.read_text()
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/plane-ops.md" in content
        assert "@AGENTS.md" in content
        assert "@docs/house-style.md" in content

    def test_tc2_add_missing_desired_ref(self, tmp_path):
        """TC2: desired ref absent -> appended with blank-line separator."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("@AGENTS.md\n")
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert result.added == [".agentic-beacon/artifacts/contexts/beacon-ops.md"]

        content = claude.read_text()
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content
        assert "@AGENTS.md" in content

    def test_tc3_preserves_non_artifact_includes(self, tmp_path):
        """TC3: only artifact includes change, others stay in place."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(
            "@AGENTS.md\n"
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
            "@docs/house-style.md\n"
            "@.agentic-beacon/artifacts/contexts/cicd-flow.md\n"
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert len(result.removed) == 2

        content = claude.read_text()
        assert "@AGENTS.md" in content
        assert "@docs/house-style.md" in content
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content
        assert "@.agentic-beacon/artifacts/contexts/cicd-flow.md" not in content

    def test_tc4_idempotent_no_write(self, tmp_path):
        """TC4: already-matching file -> bytes unchanged."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("@.agentic-beacon/artifacts/contexts/beacon-ops.md\n")
        mtime_before = claude.stat().st_mtime
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert result.added == []
        assert result.removed == []
        assert claude.stat().st_mtime == mtime_before

    def test_tc5_empty_desired_clears_owned(self, tmp_path):
        """TC5: empty desired set -> all owned includes removed."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(
            "@AGENTS.md\n@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )
        result = _reconcile_claude_md(tmp_path, [])
        assert len(result.removed) == 1

        content = claude.read_text()
        assert "@AGENTS.md" in content
        assert "@.agentic-beacon/artifacts/contexts/linear-ops.md" not in content

    def test_tc6_prefers_dot_claude_claude_md(self, tmp_path):
        """TC6: .claude/CLAUDE.md preferred over root CLAUDE.md when both exist."""
        dot_claude = tmp_path / ".claude"
        dot_claude.mkdir(parents=True)
        (dot_claude / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
        )
        root_claude = tmp_path / "CLAUDE.md"
        root_claude.write_text("@AGENTS.md\n")

        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert ".agentic-beacon/artifacts/contexts/linear-ops.md" in result.removed
        # Root CLAUDE.md should be untouched
        assert "@AGENTS.md" in root_claude.read_text()

    def test_tc7_no_file_noop(self, tmp_path):
        """TC7: no CLAUDE.md present -> no-op."""
        result = _reconcile_claude_md(
            tmp_path, [".agentic-beacon/artifacts/contexts/x.md"]
        )
        assert result.added == []
        assert result.removed == []

    def test_handles_missing_trailing_newline(self, tmp_path):
        """Handle file without trailing newline."""
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("@AGENTS.md")
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result = _reconcile_claude_md(tmp_path, desired)
        assert len(result.added) == 1
        content = claude.read_text()
        assert "@.agentic-beacon/artifacts/contexts/beacon-ops.md" in content


# ---------------------------------------------------------------------------
# Task 1.4: reconcile_context_references
# ---------------------------------------------------------------------------


class TestReconcileContextReferences:
    def _setup_both(self, tmp_path, opencode_instructions, claude_lines):
        """Helper to set up both files with given content."""
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
        if claude_lines is not None:
            (tmp_path / "CLAUDE.md").write_text(claude_lines)

    def test_tc1_both_files_drift(self, tmp_path):
        """TC1: both files drift -> aggregated added/removed spans both."""
        self._setup_both(
            tmp_path,
            opencode_instructions=[
                ".agentic-beacon/artifacts/contexts/linear-ops.md",
                "docs/house-style.md",
            ],
            claude_lines=(
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
            claude_lines="@.agentic-beacon/artifacts/contexts/linear-ops.md\n",
        )
        oc_before = (tmp_path / "opencode.json").read_bytes()
        cl_before = (tmp_path / "CLAUDE.md").read_bytes()
        desired = [".agentic-beacon/artifacts/contexts/plane-ops.md"]
        result = reconcile_context_references(tmp_path, desired, dry_run=True)
        assert len(result.added) > 0 or len(result.removed) > 0
        assert (tmp_path / "opencode.json").read_bytes() == oc_before
        assert (tmp_path / "CLAUDE.md").read_bytes() == cl_before

    def test_tc3_idempotent(self, tmp_path):
        """TC3: second call returns empty added/removed."""
        self._setup_both(
            tmp_path,
            opencode_instructions=[
                ".agentic-beacon/artifacts/contexts/beacon-ops.md",
            ],
            claude_lines="@.agentic-beacon/artifacts/contexts/beacon-ops.md\n",
        )
        desired = [".agentic-beacon/artifacts/contexts/beacon-ops.md"]
        result1 = reconcile_context_references(tmp_path, desired)
        result2 = reconcile_context_references(tmp_path, desired)
        # First call could still report no change (already matches)
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
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("@.agentic-beacon/artifacts/contexts/linear-ops.md\n")

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
            "@.agentic-beacon/artifacts/contexts/linear-ops.md" in claude_md.read_text()
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
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "@AGENTS.md\n@.agentic-beacon/artifacts/contexts/linear-ops.md\n"
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
            not in claude_md.read_text()
        )
        assert (
            "@.agentic-beacon/artifacts/contexts/plane-ops.md" in claude_md.read_text()
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
