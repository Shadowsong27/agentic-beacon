"""Copy (or check) shared scripts from _shared/scripts/ into each skill's scripts/ dir.

Usage:
    python libs/beacon/scripts/sync_shared_scripts.py           # copy mode
    python libs/beacon/scripts/sync_shared_scripts.py --check   # check mode (exit 1 on drift)
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CANONICAL_DIR = (
    _REPO_ROOT
    / "libs"
    / "beacon"
    / "src"
    / "beacon"
    / "data"
    / "skills"
    / "_shared"
    / "scripts"
)
_SKILL_TARGETS = ["record-skill", "record-knowledge"]
_SKILLS_BASE = _REPO_ROOT / "libs" / "beacon" / "src" / "beacon" / "data" / "skills"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_copy() -> None:
    for skill in _SKILL_TARGETS:
        target_dir = _SKILLS_BASE / skill / "scripts"
        target_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(_CANONICAL_DIR.iterdir()):
            dst = target_dir / src.name
            shutil.copy2(src, dst)
            print(f"COPIED: {dst.relative_to(_REPO_ROOT)}")


def run_check() -> int:
    exit_code = 0
    for skill in _SKILL_TARGETS:
        target_dir = _SKILLS_BASE / skill / "scripts"
        for src in sorted(_CANONICAL_DIR.iterdir()):
            dst = target_dir / src.name
            if not dst.exists():
                print(f"DRIFT: {dst.relative_to(_REPO_ROOT)} (missing)")
                exit_code = 1
            elif _sha256(src) != _sha256(dst):
                print(f"DRIFT: {dst.relative_to(_REPO_ROOT)}")
                exit_code = 1
            else:
                print(f"OK: {dst.relative_to(_REPO_ROOT)}")
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: exit 1 if any skill copy diverges from canonical.",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(run_check())
    else:
        run_copy()


if __name__ == "__main__":
    main()
