# Open Questions

Aspects of the codebase where the design is unclear, subject to change, or not yet documented.
Contributors who resolve these should update the relevant docs and remove the entry here.

---

## Warehouse Init Structure

The exact directory and file structure created by `abc warehouse init` is not documented.
Refer to `libs/beacon/src/beacon/domains/setup/initializer.py` for the current implementation.

**Impact:** Contributors wanting to document expected warehouse layout or write tests for the
init command need to read the source directly.

---

## Architecture Waiver Cleanup

Three CLI handlers violate the single-domain-call rule (tracked in `_TC9B_WAIVERS`):

- `sync.py::sync` — multiple domain calls
- `sync.py::status` — multiple domain calls
- `adoption.py::adopt` — multiple domain calls

These are annotated with `# TODO` comments and `PER-120` / related ticket references.
The intended resolution is to collapse the multiple calls into single orchestrating domain
functions. No timeline is set.

Five domain files violate the no-CLI-imports rule (tracked in `_TC10_WAIVERS`):

- `adoption/apply.py` — imports `click`, `rich`
- `artifact/skill.py` — imports `rich`, calls `sys.exit`
- `distribution/upgrader.py` — imports `click`
- `setup/wiring.py` — imports `click`, `rich`
- `warehouse/catalog.py` — imports `rich`

---

## Coverage Gate

There is currently no minimum test coverage gate in CI. Coverage is reported but not enforced.
Whether to add a threshold and what it should be is an open question.

---

## Type Checking

There is no mypy or pyright configuration. Type annotations are present throughout the codebase
but not validated by CI. Adding a type checker is an open design question.

---

## `PER-NNN` Ticket System

Code references `PER-NNN` identifiers (e.g., `PER-132`, `PER-127`) linking to the internal
OpenSpec change system under `openspec/`. The full relationship between code TODOs and OpenSpec
changes is not documented for external contributors.
