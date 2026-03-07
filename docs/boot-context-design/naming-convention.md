# Context File Naming Convention

## Overview

Context files use different naming conventions at different levels to optimize for their specific use cases.

---

## Warehouse Level: Simple, Flexible Names

**Location:** `contexts/` directory in warehouse repository

**Convention:** Simple, descriptive filenames without prefixes

**Examples:**
- `global.md` - Universal standards for all projects
- `python.md` - Python language standards
- `typescript.md` - TypeScript language standards
- `data-platform.md` - Data platform domain patterns
- `web-app.md` - Web application domain patterns

**Why:**
- Cleaner, less verbose
- More flexible (teams can name descriptively: `python-standards.md`, `backend-patterns.md`)
- Directory name `contexts/` already indicates purpose
- Files are loaded via `opencode.json` configuration, not by filename convention

**Example warehouse structure:**
```
contexts/
├── global.md
├── python.md
├── typescript.md
├── data-platform.md
└── web-app.md
```

---

## Project Level: Convention AGENTS.md

**Location:** `<project-root>/.opencode/AGENTS.md`

**Convention:** Single file named `AGENTS.md`

**Why:**
- Immediately recognizable as boot context
- Standard location makes it easy to find
- Convention signals "this is agent instructions"
- Single file keeps project-specific context consolidated

**Example project structure:**
```
my-project/
├── .opencode/
│   ├── AGENTS.md          ← Project-specific context
│   ├── opencode.json      ← References warehouse contexts
│   └── skills/            ← Project skills
└── src/
```

**Example opencode.json:**
```json
{
  "instructions": [
    "~/.agentic-context/global.md",
    "~/.agentic-context/python.md",
    "~/.agentic-context/data-platform.md",
    ".opencode/AGENTS.md"
  ]
}
```

---

## User Level: Convention AGENTS.md

**Location:** `~/.config/opencode/AGENTS.md`

**Convention:** Single file named `AGENTS.md`

**Why:**
- Same reasons as project level
- Personal preferences file
- Clear convention across all user machines

**Example user structure:**
```
~/.config/opencode/
└── AGENTS.md              ← Personal preferences
```

---

## Load Order

When an agent starts, contexts load in this order:

```
1. Warehouse contexts (via opencode.json)
   ├── ~/.agentic-context/global.md
   ├── ~/.agentic-context/python.md
   └── ~/.agentic-context/data-platform.md

2. User preferences (if exists)
   └── ~/.config/opencode/AGENTS.md

3. Project context (last, can override)
   └── .opencode/AGENTS.md
```

**Precedence:** Later files can override earlier files.

---

## Summary Table

| Level | Location | Naming | Example | Why |
|-------|----------|--------|---------|-----|
| **Warehouse** | `warehouse/contexts/` | Simple, flexible | `python.md`, `data-platform.md` | Cleaner, configured via opencode.json |
| **Project** | `<project>/.opencode/` | Convention: `AGENTS.md` | `AGENTS.md` | Standard, recognizable, consolidated |
| **User** | `~/.config/opencode/` | Convention: `AGENTS.md` | `AGENTS.md` | Standard, recognizable, personal |

---

## Migration from Old Convention

If you're upgrading from the old `AGENTS.*.md` convention:

**Old warehouse structure:**
```
contexts/
├── AGENTS.global.md
├── AGENTS.python.md
└── AGENTS.data-platform.md
```

**New warehouse structure:**
```
contexts/
├── global.md
├── python.md
└── data-platform.md
```

**Update opencode.json references:**
```json
{
  "instructions": [
    "~/.agentic-context/global.md",           // Changed
    "~/.agentic-context/python.md",           // Changed
    "~/.agentic-context/data-platform.md",    // Changed
    ".opencode/AGENTS.md"                     // Unchanged
  ]
}
```

---

## Benefits of This Convention

**Warehouse level:**
- ✅ Cleaner, less verbose filenames
- ✅ Flexibility in naming (teams choose what makes sense)
- ✅ Reduced redundancy (directory already says "contexts")

**Project/User level:**
- ✅ Standard convention across all projects
- ✅ Easy to find (everyone knows to look for AGENTS.md)
- ✅ Signals "this is boot context for agents"
- ✅ Single file keeps content consolidated

**Overall:**
- ✅ Best of both worlds: flexibility where needed, convention where helpful
- ✅ Configuration-driven (opencode.json) instead of filename-driven
- ✅ Clear separation of concerns across tiers
