"""Tests for shared file filters that exclude OS litter from skill operations."""

import shutil

from beacon.core.file_filter import (
    SKILL_IGNORE_NAMES,
    SKILL_IGNORE_PATTERNS,
    is_skill_file,
)


def test_ignore_names_contains_ds_store():
    assert ".DS_Store" in SKILL_IGNORE_NAMES
    assert "Thumbs.db" in SKILL_IGNORE_NAMES


def test_is_skill_file_returns_true_for_regular_files(temp_dir):
    skill_md = temp_dir / "SKILL.md"
    skill_md.write_text("content")
    assert is_skill_file(skill_md)


def test_is_skill_file_returns_false_for_ds_store(temp_dir):
    ds_store = temp_dir / ".DS_Store"
    ds_store.write_text("")
    assert not is_skill_file(ds_store)


def test_is_skill_file_returns_false_for_thumbs_db(temp_dir):
    thumbs = temp_dir / "Thumbs.db"
    thumbs.write_text("")
    assert not is_skill_file(thumbs)


def test_is_skill_file_returns_false_for_directories(temp_dir):
    subdir = temp_dir / "scripts"
    subdir.mkdir()
    assert not is_skill_file(subdir)


def test_is_skill_file_returns_false_for_missing_file(temp_dir):
    assert not is_skill_file(temp_dir / "nonexistent")


def test_copytree_ignore_patterns_filters_ds_store(temp_dir):
    src = temp_dir / "src"
    dst = temp_dir / "dst"
    src.mkdir()
    (src / "SKILL.md").write_text("hello")
    (src / ".DS_Store").write_text("")

    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKILL_IGNORE_PATTERNS))

    assert (dst / "SKILL.md").exists()
    assert not (dst / ".DS_Store").exists()
