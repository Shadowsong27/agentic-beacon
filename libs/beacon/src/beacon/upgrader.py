"""Warehouse template upgrade logic."""

import difflib
from enum import Enum
from pathlib import Path
from typing import Any

import click

from .checksums import compute_sha256, read_checksums, write_checksums
from .data.historical_hashes import is_known_hash, normalise_path
from .initializer import _TEMPLATES_DIR, TEMPLATE_FILES


class FileState(str, Enum):
    UNMODIFIED = "unmodified"
    USER_MODIFIED = "user-modified"
    LEGACY_UNMODIFIED = "legacy-unmodified"
    LEGACY_UNKNOWN = "legacy-unknown"


class WarehouseUpgrader:
    """Upgrades template-generated files in an existing warehouse."""

    def __init__(self, warehouse_path: Path):
        self.warehouse_path = warehouse_path
        self._stored_checksums: dict[str, str] | None = read_checksums(warehouse_path)

    def classify_file(self, rel_path: str) -> FileState:
        """Classify a template file's modification state.

        Args:
            rel_path: Relative path from warehouse root (forward-slash).

        Returns:
            FileState enum value.

        Raises:
            FileNotFoundError: If the file does not exist on disk.
        """
        path = self.warehouse_path / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {path}")

        on_disk_sha = compute_sha256(path.read_text(encoding="utf-8"))
        norm = normalise_path(rel_path)

        if self._stored_checksums is not None:
            stored = self._stored_checksums.get(norm)
            if stored is None:
                return FileState.USER_MODIFIED
            return (
                FileState.UNMODIFIED
                if on_disk_sha == stored
                else FileState.USER_MODIFIED
            )

        # Legacy warehouse — no checksum file
        if is_known_hash(norm, on_disk_sha):
            return FileState.LEGACY_UNMODIFIED
        return FileState.LEGACY_UNKNOWN

    def _read_new_template(
        self, rel_path: str, template_overrides: dict[str, str]
    ) -> str:
        """Return new template content for *rel_path*.

        Falls back to the packaged template file when no override is supplied.
        """
        if rel_path in template_overrides:
            return template_overrides[rel_path]
        tmpl_path = _TEMPLATES_DIR / rel_path
        if tmpl_path.exists():
            return tmpl_path.read_text(encoding="utf-8")
        return ""

    def run(
        self,
        *,
        template_overrides: dict[str, str] | None = None,
        dry_run: bool = False,
        force: bool = False,
        interactive: bool = False,
    ) -> dict[str, Any]:
        """Run the upgrade loop over all tracked template files.

        Args:
            template_overrides: Map of rel_path → new content (used in tests).
            dry_run: Print planned actions but write nothing.
            force: Overwrite all files regardless of classification.
            interactive: Prompt per-file when a modification is detected.

        Returns:
            Summary dict with keys: upgraded, skipped, sidecar_written, sidecar_skipped.
        """
        overrides = template_overrides or {}
        stats: dict[str, int] = {
            "upgraded": 0,
            "skipped": 0,
            "sidecar_written": 0,
            "sidecar_skipped": 0,
        }
        # Track hashes only for files we actually write (not skipped/sidecar files).
        # This preserves the original template hash for user-modified files so future
        # runs continue to correctly classify them as modified.
        upgraded_hashes: dict[str, str] = {}

        for rel in TEMPLATE_FILES:
            path = self.warehouse_path / rel

            new_content = self._read_new_template(rel, overrides)
            if not new_content:
                continue

            if not path.exists():
                # Distinguish a new template (never existed here) from a user-deleted one.
                # If rel is absent from the stored checksums, this warehouse has never had
                # this file → it was added in a newer abc version → create it.
                # If rel IS in the stored checksums, the user deleted it → respect that.
                norm = normalise_path(rel)
                was_present = (
                    self._stored_checksums is not None
                    and norm in self._stored_checksums
                )
                if was_present:
                    click.echo(f"↷ Skipped {rel} (deleted by user)")
                    stats["skipped"] += 1
                    continue
                # New template — create the parent dir if needed and write it.
                path.parent.mkdir(parents=True, exist_ok=True)
                label = "[would add]" if dry_run else "✓ Added"
                click.echo(f"{label} {rel} (new template)")
                if not dry_run:
                    path.write_text(new_content, encoding="utf-8")
                    stats["upgraded"] += 1
                    upgraded_hashes[rel] = compute_sha256(new_content)
                continue

            state = self.classify_file(rel)
            upgraded = False

            if force:
                self._write_file(path, new_content, rel, dry_run, "(force)", stats)
                upgraded = True
            elif state in (FileState.UNMODIFIED, FileState.LEGACY_UNMODIFIED):
                tag = (
                    "(legacy warehouse)" if state == FileState.LEGACY_UNMODIFIED else ""
                )
                self._write_file(path, new_content, rel, dry_run, tag, stats)
                upgraded = True
            else:
                # user-modified or legacy-unknown
                if interactive:
                    before = stats["upgraded"]
                    self._interactive_prompt(path, rel, new_content, dry_run, stats)
                    upgraded = stats["upgraded"] > before
                else:
                    self._write_sidecar(path, rel, new_content, dry_run, stats)

            if not dry_run and upgraded:
                upgraded_hashes[rel] = compute_sha256(new_content)

        if not dry_run:
            # Merge with existing stored checksums so skipped files retain their
            # original template hash (enabling future upgrade runs to still detect them).
            merged: dict[str, str] = dict(self._stored_checksums or {})
            merged.update(upgraded_hashes)
            write_checksums(self.warehouse_path, merged)

        upgraded = stats["upgraded"]
        skipped = stats["skipped"] + stats["sidecar_written"] + stats["sidecar_skipped"]
        click.echo(
            f"Template upgrade {'(dry-run) ' if dry_run else ''}complete. "
            f"{upgraded} upgraded, {skipped} skipped "
            f"(see *.new files)."
        )
        return stats

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_file(
        self,
        path: Path,
        new_content: str,
        rel: str,
        dry_run: bool,
        tag: str,
        stats: dict[str, int],
    ) -> None:
        label = "[would upgrade]" if dry_run else "✓ Upgraded"
        click.echo(f"{label} {rel} {tag}".strip())
        if not dry_run:
            path.write_text(new_content, encoding="utf-8")
            stats["upgraded"] += 1

    def _write_sidecar(
        self,
        path: Path,
        rel: str,
        new_content: str,
        dry_run: bool,
        stats: dict[str, int],
    ) -> None:
        sidecar = Path(str(path) + ".new")
        if dry_run:
            click.echo(f"[would write .new sidecar] {rel}")
            return
        if sidecar.exists():
            click.secho(
                f"⚠ {rel}.new already exists — skipping sidecar write.", fg="yellow"
            )
            stats["sidecar_skipped"] += 1
            return
        sidecar.write_text(new_content, encoding="utf-8")
        click.secho(
            f"⚠ {rel} was modified. New template written to {rel}.new — merge manually.",
            fg="yellow",
        )
        stats["sidecar_written"] += 1

    def _interactive_prompt(
        self,
        path: Path,
        rel: str,
        new_content: str,
        dry_run: bool,
        stats: dict[str, int],
    ) -> None:
        current = path.read_text(encoding="utf-8")
        diff = list(
            difflib.unified_diff(
                current.splitlines(),
                new_content.splitlines(),
                fromfile="Current (Modified)",
                tofile="New Template",
                lineterm="",
            )
        )
        for line in diff:
            color = (
                "red"
                if line.startswith("-")
                else "green"
                if line.startswith("+")
                else None
            )
            click.secho(line, fg=color)

        if dry_run:
            click.echo(f"[would prompt] {rel}")
            return

        if click.confirm(f"Overwrite {rel} with new template?"):
            path.write_text(new_content, encoding="utf-8")
            click.echo(f"✓ Upgraded {rel}")
            stats["upgraded"] += 1
        else:
            self._write_sidecar(path, rel, new_content, dry_run, stats)
