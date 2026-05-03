#!/usr/bin/env bash
# check_legacy_docs.sh — hard-gate grep sweep for legacy copy/contribute/delta terminology.
#
# CI runs this from the repo root. Exits 0 on clean sweep, 1 on any hit
# outside allowlisted zones (archive/, openspec/changes/*/).
#
# See: openspec/changes/symlink-based-artifact-sync/tasks.md task 9.11
#      knowledge/decisions/single-warehouse-write-entrypoint.md
#
# Usage:
#   scripts/check_legacy_docs.sh
#   scripts/check_legacy_docs.sh --verbose    # show context
#
# Exit codes:
#   0 — no hits outside allowlisted zones
#   1 — one or more hits require resolution
#   2 — tooling error (ripgrep missing, wrong cwd, etc.)

set -euo pipefail

VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --verbose|-v) VERBOSE=1 ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      echo "error: unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

if ! command -v rg >/dev/null 2>&1; then
  echo "error: ripgrep (rg) is required. Install via 'brew install ripgrep'." >&2
  exit 2
fi

# Must be run from repo root (where this script's parent dir is `scripts/`).
if [[ ! -d "scripts" || ! -d "libs/beacon" ]]; then
  echo "error: run from repo root (expected scripts/ and libs/beacon/ to exist)" >&2
  exit 2
fi

# Patterns to check. Each entry is "LABEL|REGEX".
#
# Rules:
# - Patterns must be precise enough to avoid false positives on legitimate prose
#   (e.g., "copy" in "copy the text" is fine; "copies files" in a sync context is not).
# - The first three patterns are command names and always wrong outside allowlisted zones.
# - The remaining patterns are context-sensitive; tune the regex rather than
#   broadening the allowlist.
PATTERNS=(
  "bare 'abc contribute'|\\babc contribute\\b"
  "'abc delta'|\\babc delta\\b"
  "'abc sync --preserve' (flag removed)|abc sync --preserve\\b"
  "'sync --preserve' in prose|\\bsync --preserve\\b"
  "copy-model phrasing in sync context|sync (copies|copied)\\b"
  "snapshot phrasing in sync context|snapshot (of|semantics|at time of sync)"
  "project isolation phrasing|(project isolation\\b|local cop(y|ies) of (the )?warehouse)"
)

# Allowlisted zones — legacy terminology is expected and acceptable here.
# These are passed as ripgrep --glob '!<zone>' exclusions.
ALLOWLIST_GLOBS=(
  '!archive/**'
  '!openspec/changes/**'
  '!openspec/specs/snapshot-based-sync/**'        # superseded spec, slated for archival in task 10.4
  '!openspec/specs/delta-contribution-workflow/**' # superseded spec, slated for archival in task 10.4
  '!openspec/specs/contribute-noop/**'              # orphaned by abc contribute removal; archive in task 10.4
  '!openspec/specs/global-agent-delta/**'           # orphaned by abc delta removal; archive in task 10.4
  '!openspec/specs/global-agent-sync-state/**'      # rewritten in-place; historical-context note legitimately names removed commands
  '!openspec/specs/sync-soft-block/**'              # rewritten in-place; historical-context note legitimately names removed commands
  '!openspec/specs/install-flags/**'                # rewritten in-place; historical-context note legitimately names removed commands
  # Test files: test names, fixtures, and assertions legitimately reference old behavior
  # when testing deprecation stubs or migration paths. Test authors own their comments.
  '!libs/beacon/tests/**'
  '!site/**'           # mkdocs build output, regenerated on release
  '!site-docs/**'      # mkdocs source — handled in a separate follow-up session
  '!.venv/**'
  '!.ruff_cache/**'
  '!.pytest_cache/**'
  '!.git/**'
  '!dist/**'
  # This script itself legitimately contains every pattern as string literals.
  '!scripts/check_legacy_docs.sh'
  # Deprecation stubs legitimately name the removed commands to tell users what to use instead.
  '!libs/beacon/src/beacon/cli/main.py'
  # The decision record explaining the deprecation must name the removed commands.
  '!knowledge/decisions/single-warehouse-write-entrypoint.md'
  # Release-Please auto-generates CHANGELOG entries from conventional commits; breaking-change
  # entries will legitimately name removed commands.
  '!libs/beacon/CHANGELOG.md'
)

GLOB_ARGS=()
for glob in "${ALLOWLIST_GLOBS[@]}"; do
  GLOB_ARGS+=("--glob" "$glob")
done

fail_count=0

for entry in "${PATTERNS[@]}"; do
  label="${entry%%|*}"
  regex="${entry#*|}"

  if [[ "$VERBOSE" -eq 1 ]]; then
    hits="$(rg --color=never --line-number --no-heading "${GLOB_ARGS[@]}" -e "$regex" . || true)"
  else
    hits="$(rg --color=never --files-with-matches "${GLOB_ARGS[@]}" -e "$regex" . || true)"
  fi

  if [[ -n "$hits" ]]; then
    fail_count=$((fail_count + 1))
    echo "✖ ${label}"
    echo "${hits}" | sed 's/^/    /'
    echo
  fi
done

if [[ "$fail_count" -gt 0 ]]; then
  echo "Legacy-docs sweep failed: ${fail_count} pattern(s) matched outside allowlisted zones." >&2
  echo "Resolution: rewrite the hit in place, or move the whole document under archive/ with a 'superseded by' pointer." >&2
  echo "See knowledge/decisions/single-warehouse-write-entrypoint.md and archive/README.md." >&2
  exit 1
fi

echo "✓ legacy-docs sweep clean"
exit 0
