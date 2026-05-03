"""Shim for backward compatibility during transition.

This module provides minimal stubs so that existing test imports continue
to resolve.  The real implementations were removed as part of the
symlink-based-artifact-sync change.
"""


def partition_tracked_diffs(*args, **kwargs):
    raise NotImplementedError("partition_tracked_diffs removed")


def render_skill_group(*args, **kwargs):
    raise NotImplementedError("render_skill_group removed")


def skill_entries(*args, **kwargs):
    raise NotImplementedError("skill_entries removed")


def render_knowledge_node_group(*args, **kwargs):
    raise NotImplementedError("render_knowledge_node_group removed")


def collect_artifact_paths(*args, **kwargs):
    raise NotImplementedError("collect_artifact_paths removed")


def find_untracked_local_files(*args, **kwargs):
    raise NotImplementedError("find_untracked_local_files removed")
