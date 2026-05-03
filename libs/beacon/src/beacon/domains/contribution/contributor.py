"""Shim for backward compatibility during transition.

This module provides minimal stubs so that existing test imports continue
to resolve.  The real implementations were removed as part of the
symlink-based-artifact-sync change.
"""


def build_pr_body(*args, **kwargs):
    raise NotImplementedError("build_pr_body removed")


def resolve_skill_contribute_source(*args, **kwargs):
    raise NotImplementedError("resolve_skill_contribute_source removed")


def auto_git_contribute(*args, **kwargs):
    raise NotImplementedError("auto_git_contribute removed")
