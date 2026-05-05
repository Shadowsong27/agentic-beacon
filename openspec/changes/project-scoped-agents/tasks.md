## 1. beacon.yaml schema extension

- [ ] 1.1 Add `agents: list[str]` field to `ArtifactsConfig` in `libs/beacon/src/beacon/core/manifest/beacon.py`. Default `[]`. Include in schema serialisation.
- [ ] 1.2 Update `BeaconManifest.to_yaml()` to emit the `agents:` key in the grouped `artifacts:` section, ordered after `contexts:` and `skills:`.
- [ ] 1.3 Unit tests for `BeaconManifest` round-trip with and without `agents:` (absence is valid, empty list is valid, populated list is valid).
- [ ] 1.4 Update `libs/beacon/src/beacon/domains/setup/initializer.py` so `abc setup` writes `beacon.yaml` with the `agents: []` field in the scaffold template.

## 2. Dependency resolution wiring

- [ ] 2.1 Extend `libs/beacon/src/beacon/core/dependencies/resolver.py` to accept declared agents from `beacon.yaml.artifacts.agents`. For each declared agent, load `agents.yaml` (via the loader added in the predecessor change), resolve its `skills:` list.
- [ ] 2.2 Add `validate_declared_agents_in_manifest(beacon_settings, agent_manifest)` — every path in `artifacts.agents` must have a key in `agents.yaml`; missing key is a hard error with migration URL.
- [ ] 2.3 Compute the transitive skill closure: declared explicit skills + skills required by declared agents. Carry provenance (explicit vs required-by-agent) through the resolver's data model.
- [ ] 2.4 Unit tests covering: no agents declared, one agent with skills, one agent with empty skills, agent not in manifest, skill not in warehouse, multi-agent overlapping skill requirements.

## 3. abc sync: interactive repair prompt

- [ ] 3.1 Add a new error/warning shape in `libs/beacon/src/beacon/core/dependencies/` that carries the gap info (requiring agent, missing skill, warehouse skill path).
- [ ] 3.2 In the sync flow (sync command in `domains/warehouse/` or equivalent), intercept the gap before any file operation. In interactive mode, prompt Y/N default N using `click.confirm` or existing interaction helper.
- [ ] 3.3 On Y: append the normalised skill path (`skills/<name>/`) to `beacon.yaml.artifacts.skills`, persist with `BeaconManifest.to_yaml()`, re-run the resolver with the updated state, proceed to sync.
- [ ] 3.4 On N (or Enter on default): raise a `DependencyError` carrying the migration URL; let the normal error-printing path surface it; exit non-zero.
- [ ] 3.5 Non-interactive mode (no TTY): skip the prompt; raise the same error unless `--yes` is passed.
- [ ] 3.6 Add `--yes` flag to `abc sync` CLI handler. Plumb into the resolver's prompt logic as auto-accept.
- [ ] 3.7 Unit tests for each branch: interactive Y, interactive N, interactive default-Enter, non-interactive no-flag, non-interactive with `--yes`. Use `pytest`'s `monkeypatch` to fake TTY detection and `click.testing.CliRunner` for CLI input.

## 4. Adoption flow: remove skip + record agents

- [ ] 4.1 In `libs/beacon/src/beacon/domains/adoption/apply.py::apply_adoption()`, remove the `if candidate.artifact_type == "agents": continue` skip. Extend the branch to append `candidate.path` (form `agents/<name>.md`) to `beacon_settings.artifacts.agents`; deduplicate.
- [ ] 4.2 Ensure the existing global install call path for selected agents (from the adopt apply flow) continues to fire — agents still symlink into `~/.config/opencode/agents/` and `~/.claude/agents/`.
- [ ] 4.3 Update `libs/beacon/src/beacon/domains/adoption/discovery.py::is_adopted()` to check `beacon_settings.artifacts.agents` in addition to contexts and skills.
- [ ] 4.4 Update `cleanup_unadopted_artifacts()` (and any unadopt helpers) so that removing an agent from `beacon.yaml.artifacts.agents` does NOT uninstall the global symlink; explicit comment in the code stating this is intentional (Decision 7).
- [ ] 4.5 Unit tests for apply_adoption with agent selections; assert `beacon.yaml` updated, global install triggered, no global uninstall on unadoption.

## 5. Adoption TUI: agent category + auto-tick + hard-lock

- [ ] 5.1 In `libs/beacon/src/beacon/domains/adoption/tui.py`, add an "Agents" section alongside "Contexts" and "Skills". Populate with agent candidates from `discovery.py`.
- [ ] 5.2 When an agent is ticked, read `agents.yaml` (via the warehouse client), resolve `skills:` list, programmatically tick the corresponding skill checkboxes. Record a `required_by` provenance map keyed on skill name → list of requiring agents.
- [ ] 5.3 Render provenance next to each skill checkbox when non-empty (e.g. ``(required by spec-planner, registra-developer)``). Cap display to first 3 agents with `+N more` if the list is longer.
- [ ] 5.4 Implement hard-lock: when a skill's `required_by` list is non-empty, the checkbox rejects toggle-off events. Show a transient status message ``"Required by: <agent> — untick agent first"``.
- [ ] 5.5 When an agent is unticked, remove it from every skill's `required_by` list. If a skill's `required_by` becomes empty AND the user never explicitly ticked it (tracked separately as `user_explicit`), auto-untick the skill.
- [ ] 5.6 When a skill is ticked directly by the user, set `user_explicit[skill] = True`. This survives subsequent agent unticks.
- [ ] 5.7 Update the `select all` (`a`) and `select none` (`n`) keybindings: select-all triggers agent-auto-tick propagation; select-none clears everything including provenance.
- [ ] 5.8 TUI snapshot tests or headless runs (textual's test harness) covering: tick agent → skills auto-tick with provenance; untick skill while agent ticked → blocked; untick agent → skill auto-unticks unless user-explicit; multi-agent shared skill provenance.

## 6. Warehouse `abc warehouse status` and safety checks

- [ ] 6.1 Extend `libs/beacon/src/beacon/domains/warehouse/validator.py` so `abc warehouse status` reports declared agents whose `agents.yaml` entries have missing skills, as part of the existing warehouse integrity report.
- [ ] 6.2 Confirm the "declared agent not in `agents.yaml`" error (per `validate_declared_agents_in_manifest`) surfaces with clear output.
- [ ] 6.3 Smoke tests using a fixture warehouse + project fixture.

## 7. Sample warehouse + migration doc

- [ ] 7.1 Update `examples/sample-warehouse/agents/agents.yaml` to declare an example agent with a skill requirement, demonstrating the feature end-to-end.
- [ ] 7.2 If the sample warehouse lacks a sample skill matching the declared requirement, add one (minimal `skills/<name>/SKILL.md`).
- [ ] 7.3 Append a "Project-scoped agents" section to `docs/migrations/artifact-dependencies-frontmatter.md` describing the new field, the `abc adopt` flow, the repair prompt at sync, and the zero-friction "re-run adopt" migration for existing users.

## 8. AGENTS.md & site-docs sync

- [ ] 8.1 Update `AGENTS.md` at the repo root to describe the new agent declaration field and remove any language asserting "agents are not tracked in beacon.yaml."
- [ ] 8.2 Update relevant pages under `site-docs/` that describe `beacon.yaml` schema or the adoption flow. This is the single MkDocs refresh covering both this change and the predecessor `move-agent-requires-to-warehouse-manifest` — the docs surface is updated once at the end.
- [ ] 8.3 Ensure any README snippets in the repo showing `beacon.yaml` examples include the new `agents:` line where relevant.
- [ ] 8.4 Clean up stale "agents are global-only / not in beacon.yaml" language across the code. Concrete spots:
  - `libs/beacon/src/beacon/domains/adoption/discovery.py:340` — comment `# "adopted" means installed in a global agent directory, not beacon.yaml`
  - `libs/beacon/src/beacon/domains/adoption/tui.py:137` — subtitle string `"AI agent definitions • installed globally to ..."`
  - `libs/beacon/src/beacon/domains/setup/wiring.py:21` — comment `# Agents are machine-level global artifacts — use 'abc install agents/<name>.md'`
  - `libs/beacon/src/beacon/cli/setup.py:56` — console string `"agents — globally linked on your machine with 'abc agents sync' (not in beacon.yaml)"`
  - `libs/beacon/src/beacon/data/templates/README.md:27` — section about installing global agents
  - `libs/beacon/src/beacon/data/templates/agents/README.md:9` — "Unlike other artifact types, agents are globally installed..."
  Rewrite each to reflect the dual semantics: agents are declared per-project in `beacon.yaml.artifacts.agents` AND globally installed. The `continue  # agents are managed globally` comment at `apply.py:40` is already addressed by task 4.1 (full deletion of the skip).

## 9. Release + validation

- [ ] 9.1 Run full `pytest` suite from repo root — all tests pass.
- [ ] 9.2 Run architecture test (`libs/beacon/tests/unit/test_architecture.py`) — still green.
- [ ] 9.3 Manual smoke #1: fresh project, `abc setup`, `abc adopt` — agents appear, auto-tick works, hard-lock works, `beacon.yaml` updated correctly.
- [ ] 9.4 Manual smoke #2: project with `beacon.yaml.artifacts.agents` declared, hand-remove a required skill, run `abc sync` — prompt fires, Y accepts, `beacon.yaml` updated, sync completes.
- [ ] 9.5 Manual smoke #3: same setup as #4 but in non-interactive mode (e.g. `abc sync < /dev/null`) — hard error, `beacon.yaml` unchanged.
- [ ] 9.6 Manual smoke #4: upgrade existing project that used `abc adopt` for agents pre-this-change — confirm `beacon.yaml.artifacts.agents` is empty and `abc sync` still works (global agents remain symlinked).
- [ ] 9.7 Release notes: call out the new field, the breaking change to `abc adopt` behaviour (records in `beacon.yaml`), and the repair prompt in `abc sync`.
