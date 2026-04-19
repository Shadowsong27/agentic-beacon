"""Shared path constants for the beacon package."""

from pathlib import Path

BUNDLED_DATA_DIR = Path(__file__).parent.parent / "data"
BUNDLED_SKILLS_DIR = BUNDLED_DATA_DIR / "skills"
