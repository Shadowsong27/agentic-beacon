"""One-way sync helper for shared scripts between record-skill and record-knowledge.

Usage:
    python libs/beacon/scripts/sync_skill_scripts.py --from record-skill
    python libs/beacon/scripts/sync_skill_scripts.py --from record-knowledge
    python libs/beacon/scripts/sync_skill_scripts.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = REPO_ROOT / "libs" / "beacon" / "src" / "beacon" / "data" / "skills"
SYNCED_SCRIPTS = ["append_pending.py", "resolve_warehouse.py"]
SKILL_NAMES = ["record-skill", "record-knowledge"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(skills_dir: Path = SKILLS_DIR) -> bool:
    """Return True if all synced scripts are byte-identical across both skills."""
    diverged: list[str] = []
    for script in SYNCED_SCRIPTS:
        paths = [skills_dir / skill / "scripts" / script for skill in SKILL_NAMES]
        hashes = {p: _sha256(p) for p in paths}
        unique = set(hashes.values())
        if len(unique) > 1:
            diverged.append(script)
            for path, digest in hashes.items():
                print(
                    f"  {path.relative_to(skills_dir.parent.parent.parent.parent)}: {digest[:16]}...",
                    flush=True,
                )
    if diverged:
        print(f"DRIFT DETECTED in: {', '.join(diverged)}", file=sys.stderr, flush=True)
        return False
    return True


def sync_from(source_skill: str, skills_dir: Path = SKILLS_DIR) -> None:
    """Copy synced scripts from source_skill to the other skill."""
    if source_skill not in SKILL_NAMES:
        print(
            f"Unknown skill: {source_skill!r}. Choose from: {SKILL_NAMES}",
            file=sys.stderr,
        )
        sys.exit(1)
    targets = [s for s in SKILL_NAMES if s != source_skill]
    for script in SYNCED_SCRIPTS:
        src = skills_dir / source_skill / "scripts" / script
        for target_skill in targets:
            dst = skills_dir / target_skill / "scripts" / script
            shutil.copy2(src, dst)
            print(f"Copied {src.name} → {dst.parent.parent.name}/scripts/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync shared scripts between record-skill and record-knowledge."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--from",
        dest="from_skill",
        metavar="SKILL",
        help="Copy scripts from this skill to the other (e.g. record-skill).",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Return exit code 0 if scripts are byte-identical, 1 if they diverge.",
    )
    args = parser.parse_args()

    if args.check:
        ok = check()
        sys.exit(0 if ok else 1)
    else:
        sync_from(args.from_skill)


if __name__ == "__main__":
    main()
