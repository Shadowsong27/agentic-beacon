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
