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

- Use this exact structure:

```markdown
## Findings

- [High] <short title> - `<file>:<line>`
  <1-3 sentences explaining the impact and the concrete fix.>

- [Medium] <short title> - `<file>:<line>`
  <1-3 sentences explaining the impact and the concrete fix.>

- [Low] <short title> - `<file>:<line>`
  <1-3 sentences explaining the impact and the concrete fix.>

## Open Questions

- <Only include if needed; otherwise write "None.">

## Notes

- <Optional brief residual risks, testing gaps, or "No findings." when clean.>
```

- Order findings by severity: High, then Medium, then Low.
- Use High for blockers that break core behavior, data safety, security, or CI.
- Use Medium for likely bugs, behavioral regressions, architecture violations, missing tests for changed behavior, or CLI UX regressions.
- Use Low for documentation drift, maintainability issues, or low-risk polish worth fixing before merge.
- Every finding must include a file:line reference when possible.
- If there are no findings, write `## Findings` followed by `No findings.`.
- Be concise and actionable; skip praise.
