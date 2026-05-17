"""Distribution tests for bundled skill manifest wiring (Task 9.3).

Asserts that _BUNDLED_SKILL_FILES in initializer.py includes all three
bundled skills, and that the on-disk skill directories contain the expected
files.

TDD Test Cases per tasks.md 9.3:
  TC1: _BUNDLED_SKILL_FILES contains the new entry
  TC2: SKILL.md file exists on disk at the expected path
  TC3: All four contribute-warehouse scripts exist on disk under scripts/
  TC4: All four scripts have the executable bit set (or are uv-runnable)
  TC5: Removing the manifest entry → test FAILS (negative test — see comment)
"""

from __future__ import annotations

from pathlib import Path

from beacon.domains.setup.initializer import _BUNDLED_SKILL_FILES

_BEACON_DATA_SKILLS = (
    Path(__file__).resolve().parents[4] / "src" / "beacon" / "data" / "skills"
)

_CONTRIBUTE_WAREHOUSE_DIR = _BEACON_DATA_SKILLS / "contribute-warehouse"
_EXPECTED_SCRIPTS = [
    "resolve_warehouse.py",
    "summarize_changes.py",
    "draft_commit_message.py",
    "push_warehouse.py",
]


class TestBundledSkillManifest:
    """TC1-TC4 from tasks.md 9.3 spec."""

    def test_tc1_manifest_contains_contribute_warehouse(self):
        """TC1: _BUNDLED_SKILL_FILES contains skills/contribute-warehouse/SKILL.md."""
        assert "skills/contribute-warehouse/SKILL.md" in _BUNDLED_SKILL_FILES, (
            f"Expected 'skills/contribute-warehouse/SKILL.md' in _BUNDLED_SKILL_FILES, "
            f"got: {_BUNDLED_SKILL_FILES}"
        )

    def test_tc1b_manifest_contains_all_three_skills(self):
        """TC1b: All three bundled skills are in the manifest."""
        for skill in (
            "skills/record-knowledge/SKILL.md",
            "skills/record-skill/SKILL.md",
            "skills/contribute-warehouse/SKILL.md",
        ):
            assert skill in _BUNDLED_SKILL_FILES, (
                f"Missing {skill!r} in _BUNDLED_SKILL_FILES"
            )

    def test_tc2_skill_md_exists_on_disk(self):
        """TC2: SKILL.md file exists on disk at the expected path."""
        skill_md = _CONTRIBUTE_WAREHOUSE_DIR / "SKILL.md"
        assert skill_md.is_file(), f"SKILL.md not found at {skill_md}"

    def test_tc3_all_four_scripts_exist(self):
        """TC3: All four helper scripts exist on disk under scripts/."""
        scripts_dir = _CONTRIBUTE_WAREHOUSE_DIR / "scripts"
        assert scripts_dir.is_dir(), f"scripts/ dir not found at {scripts_dir}"
        for script_name in _EXPECTED_SCRIPTS:
            script_path = scripts_dir / script_name
            assert script_path.is_file(), (
                f"Expected script {script_name!r} not found at {script_path}"
            )

    def test_tc4_scripts_are_readable_python_files(self):
        """TC4: Scripts are readable Python files (runnable via uv run)."""
        scripts_dir = _CONTRIBUTE_WAREHOUSE_DIR / "scripts"
        for script_name in _EXPECTED_SCRIPTS:
            script_path = scripts_dir / script_name
            content = script_path.read_text(encoding="utf-8")
            assert "def main" in content or "__main__" in content, (
                f"{script_name} should have a main() function or __main__ guard"
            )

    # TC5: Negative test — documented here.
    # This test is structural: if you remove "skills/contribute-warehouse/SKILL.md"
    # from _BUNDLED_SKILL_FILES, test_tc1_manifest_contains_contribute_warehouse
    # will FAIL — which is the intended catch-fidelity behaviour.
    # No separate test is needed; the positive test serves as the negative guard.


class TestDistributionContractPushWarehouse:
    """Additional distribution contract: push_warehouse.py safety guardrail."""

    def test_push_warehouse_no_destructive_ops(self):
        """TC (Task 6.6): push_warehouse.py must not contain destructive git ops in code lines."""
        script_path = _CONTRIBUTE_WAREHOUSE_DIR / "scripts" / "push_warehouse.py"
        content = script_path.read_text(encoding="utf-8")
        # Only check non-comment, non-docstring code lines for destructive ops.
        # Comments and docstrings may legitimately mention what the script avoids.
        code_lines = [
            line
            for line in content.splitlines()
            if line.strip()
            and not line.strip().startswith("#")
            and '"""' not in line
            and "'''" not in line
        ]
        code_text = "\n".join(code_lines)
        forbidden_patterns = [
            '"reset"',
            '"--force"',
            '"--amend"',
            '"push -f"',
            "'reset'",
            "'--force'",
            "'--amend'",
            "'push -f'",
        ]
        found = [p for p in forbidden_patterns if p in code_text]
        assert not found, (
            f"Destructive operation(s) found in push_warehouse.py code: {found}"
        )
