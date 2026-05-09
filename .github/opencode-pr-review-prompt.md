Review this pull request for the agentic-beacon repository.

Follow AGENTS.md and the rules in .agentic-beacon/artifacts/contexts/.
Review only the attached diff.

## Beacon-specific checks

- Layering: cli/ -> domains/ -> core/, utils/. core/ and utils/
  must NEVER import from domains/ or cli/. CLI handlers stay
  thin (parse + one domain call + format).
- Domain placement: new logic belongs in the owning domain,
  not core/ or utils/ by default.
- Imports: absolute only; never relative. __init__.py files are
  empty package markers (no re-exports, no __all__).
- adopt is intentional: warehouse-authored artifacts go through
  pending.yaml + `abc adopt`. Flag any code that auto-wires into
  beacon.yaml.
- Tests: split unit/ vs integration/. Sub-second mocked tests
  in unit/; real services in integration/.
- Conventional Commits in PR title and commits.

## Review priorities (ordered)

1. Correctness bugs and behavioral regressions
2. Architecture violations (layering, domain placement)
3. Missing/weak tests for changed behavior
4. CLI UX changes (flags, output, exit codes)
5. Security/safety issues
6. Documentation drift when behavior changes

## Output

- Findings first, ordered by severity.
- File:line references where possible.
- If no findings, say so explicitly.
- Be concise and actionable; skip praise.
