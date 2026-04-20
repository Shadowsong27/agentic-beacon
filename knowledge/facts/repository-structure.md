# Fact: Repository Structure

**Last Updated:** 2026-04-20
**Context:** Agentic Beacon Framework

---

## Structure

```
agentic-beacon/
├── .github/workflows/    # CI/CD workflows only (yml files, no markdown docs)
├── docs/                 # Design documentation
├── examples/             # Sample warehouse from abc init
│   └── sample-warehouse/
├── guides/               # User guides
├── knowledge/            # Project knowledge (decisions, lessons, facts)
│   ├── decisions/
│   ├── lessons/
│   └── facts/
├── libs/beacon/          # CLI source code
│   └── src/beacon/
│       ├── cli/          # Click handlers (thin layer: parse + call + format)
│       │   ├── main.py       # Click group + registration only
│       │   ├── setup.py      # abc init, abc setup handlers
│       │   ├── sync.py       # abc sync, abc doctor, abc upgrade handlers
│       │   ├── contribute.py # abc contribute handlers
│       │   ├── adoption.py   # abc adopt handlers
│       │   ├── agent.py      # abc agent handlers
│       │   └── warehouse.py  # abc warehouse handlers
│       ├── domains/      # Application / domain logic per bounded context
│       │   ├── warehouse/    # Warehouse connect, validate, catalog, git health
│       │   ├── setup/        # abc init/setup flows; CLAUDE.md/opencode wiring
│       │   ├── adoption/     # abc adopt flow
│       │   ├── distribution/ # Warehouse→project sync, upgrades, sync-state
│       │   ├── contribution/ # Project→warehouse contribute flow
│       │   └── artifact/     # Agent/skill/rule artifact operations
│       ├── core/         # Cross-domain primitives (models, settings, exceptions)
│       │   ├── manifest/     # Pydantic domain models
│       │   ├── settings.py
│       │   ├── exceptions.py
│       │   └── gitignore.py
│       ├── utils/        # Generic helpers (git, display, interaction)
│       └── data/skills/  # Bundled skills (SSOT for distributed skills)
│           └── record-knowledge/
├── openspec/             # OpenSpec change artifacts
│   ├── changes/          # Active changes
│   └── specs/            # Published specifications
├── skills/               # Project skills README only (no bundled skills here)
├── AGENTS.md             # Project-level agent context
├── opencode.json         # Context loading configuration
└── README.md             # Framework overview
```

## Directory Purposes

**Source Code:**
- `libs/beacon/` - The CLI package source code
- Follows a four-layer architecture: `cli/` → `domains/` → `core/`, `utils/`

**Documentation:**
- `docs/` - Conceptual design and architecture documentation
- `guides/` - Practical how-to guides for users
- `examples/` - Sample output from `abc init` command

**Knowledge:**
- `knowledge/` - Atomic knowledge files (decisions, lessons, facts)
  - Project cannot use its own framework, so stores knowledge locally
  - Organized by type (decisions, lessons, facts)

**Skills:**
- `libs/beacon/src/beacon/data/skills/` - SSOT for all bundled/distributed skills
  - `record-knowledge/` - Skill to capture new knowledge systematically
  - These are bundled into the package and copied into every new warehouse by `abc init`
- `skills/` - Contains only a README; no skill files live here

**Configuration:**
- `AGENTS.md` - Project context loaded on session start
- `opencode.json` - Declares context loading order
- `.github/workflows/` - CI/CD automation (yml files only)

## Important Notes

- This is **NOT a warehouse** - it's the framework source
- Users create warehouses with `abc init`
- No temporary documentation in workflows folder
- Examples must match `abc init` output
- Dependency rule: `cli → domains → core, utils`; `core/` and `utils/` must never import from `domains/` or `cli/`
