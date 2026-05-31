# Pre-commit Hook

CI is the truth source — it runs on every PR and gates merges. A pre-commit hook is the local optimisation: same lint, sub-second, fails the commit before you even push. Together they form belt-and-suspenders: pre-commit catches it on the contributor's machine, CI catches it for everyone who skips the hook.

## When to use

- **Recommended** for any warehouse contributor who runs `pre-commit install` as part of their workflow.
- **Required** if your warehouse lives in an air-gapped environment — the hook is the only local enforcement layer until the PR reaches your private CI mirror.
- **Optional but cheap** for warehouses where CI is the only enforcement point — adds ~800ms to a `git commit`, saves a CI round-trip on issues you would have caught.

---

## Drop-in config

The hook shells out to the `abc` binary contributors already have installed (per the [Installation](../../installation.md) page) — pre-commit doesn't manage its own copy. This works identically for connected and air-gapped environments; the only difference is how `agentic-beacon` reaches `PATH` (PyPI vs offline bundle), which `installation.md` covers.

Add `.pre-commit-config.yaml` to your warehouse root:

```yaml
repos:
  - repo: local
    hooks:
      - id: warehouse-lint
        name: warehouse lint
        entry: abc warehouse lint .
        language: system
        pass_filenames: false
        always_run: true
```

Each contributor (one-time):

```bash
# 1. Install agentic-beacon globally (see Installation page for connected
#    vs offline-bundle variants).
uv tool install agentic-beacon                        # connected
# OR
uv tool install --reinstall --no-index --find-links ./bundle agentic-beacon  # air-gapped

# 2. Install pre-commit (uv tool install or your team's private mirror)
#    and wire the hook into git:
uv tool install pre-commit
pre-commit install
```

From then on, every `git commit` runs the lint against the whole working tree. A failure aborts the commit; fix the artifact and re-commit.

For fixable malformed cross-artifact-relative links, the local repair path is:

```bash
abc warehouse lint --fix .
```

This rewrites only the canonicalizable link category. Keep the hook itself read-only;
the commit should fail fast and let the contributor decide when to apply the rewrite.

---

## Field rationale

| Field | Why |
|---|---|
| `repo: local` | Self-contained in the warehouse — no dependency on `agentic-beacon`'s release surface, and no GitHub access required (which would break air-gapped). See [Why not a published pre-commit hook?](#why-not-a-published-pre-commit-hook) for the longer rationale. |
| `language: system` | Pre-commit invokes the system `abc` binary directly — no isolated env, no pip, no duplicate install. The contributor already has `abc` on `PATH` because they need it for `abc warehouse connect`, `abc sync`, etc. — so pre-commit reuses the same binary. Hook version automatically tracks the contributor's globally-installed version, so the lint at commit time is the same lint they run interactively. |
| `pass_filenames: false` | Without this, pre-commit appends staged filenames to `entry`, which would call `abc warehouse lint . file1 file2 …`. Suppressing keeps the invocation to the canonical `abc warehouse lint .`. |
| `always_run: true` | Runs the hook even when no warehouse-touching files are staged (the linter validates the dependency graph, not individual files — a delete in one place can break a `requires:` reference elsewhere). |

### "abc: command not found" or "No such command 'lint'"

The hook assumes a recent `agentic-beacon` is on `PATH`. If a contributor sees either error, they need to (re)install `agentic-beacon` per the [Installation](../../installation.md) page. The `warehouse lint` subcommand requires `agentic-beacon >= 3.4.0`.

---

## The whole-tree gotcha

`abc warehouse lint .` validates the **entire working tree**, not just staged files. That means:

- If you stage a fix to `skills/foo/SKILL.md` while `skills/bar/SKILL.md` already has broken frontmatter on disk, the hook fails the commit for `bar` too.
- Usually what you want — the warehouse-wide invariant is what you're protecting.
- Escape hatch when you really need to commit through a known unrelated breakage:
  ```bash
  git stash --keep-index
  git commit -m "fix(foo): …"   # pre-commit only sees the staged 'foo' fix
  git stash pop
  ```

If this trips contributors regularly, that's a signal `main` is broken — fix the underlying artifact instead of teaching everyone to skip the hook.

---

## Why not a published pre-commit hook?

The canonical pre-commit pattern (used by ruff, black, mypy) is for the tool's source repo to publish a `.pre-commit-hooks.yaml` and have consumers reference it via `repo: https://github.com/...` + `rev:`. That pattern exists to let consumers run a tool without installing it.

`agentic-beacon` doesn't fit that premise: anyone touching a warehouse already has `abc` installed locally — they need it for `abc warehouse connect`, `abc sync`, `abc adopt`, and authoring skills. A published hook would either re-install the same binary inside pre-commit's pip env (duplication + version-skew risk) or add a `github.com` dependency for zero benefit (and break air-gapped warehouses). `repo: local` + `language: system` avoids both.

---

## Skipping the hook on a single commit

When a hook fires on something you intentionally want to defer (rare but real — e.g. a mid-refactor checkpoint):

```bash
git commit --no-verify -m "wip: …"
```

Use sparingly. Every `--no-verify` is a future "why did this slip through CI" investigation.

---

## Pair with CI

The pre-commit hook is the local optimisation. The [GitHub Actions workflow](github-actions.md) is the canonical enforcement that catches every contribution from every angle — including PRs from contributors who haven't run `pre-commit install`. Run both.
