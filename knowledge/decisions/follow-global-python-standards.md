# Decision: Follow Global Python Standards

**Date:** 2026-03-07
**Status:** Active
**Context:** Agentic Beacon Framework

---

## Context

The Agentic Beacon project is developed by a user who has comprehensive Python coding standards defined in their global AGENTS.md context.

## Decision

Follow the global Python standards from the user's AGENTS.md context rather than redefining them in this project.

## Standards Applied

- Type annotations without quotes (unless forward references)
- Use primitive types (`list`, `dict`) over typing module types (`List`, `Dict`)
- Pydantic BaseModel for data carriers
- Dataclass for service classes only
- Conventional commits for all changes

### Import Style

**Always use absolute imports** starting from the `beacon` package root. Never use relative imports (no `from ..utils import`, no `from .core import`).

```python
# correct
from beacon.core.manifest.beacon import BeaconManifest
from beacon.utils.git import find_project_root

# wrong
from ..core.manifest import BeaconManifest
from .utils.git import find_project_root
```

### `__init__.py` Policy

`__init__.py` files must **not** re-export names from sub-modules. They exist only to mark a directory as a package and may contain a docstring. Do not add `from .module import X` or `__all__` lists unless explicitly instructed.

```python
# correct — __init__.py
"""Package description."""

# wrong — __init__.py
from .beacon import BeaconManifest, ArtifactsConfig
from .workspace import WorkspaceConfig

__all__ = ["BeaconManifest", "WorkspaceConfig"]
```

Callers must import directly from the module that defines the name:

```python
# correct — import from the defining module
from beacon.core.manifest.beacon import BeaconManifest
from beacon.warehouse.validator import WarehouseValidator

# wrong — importing through a re-exporting __init__
from beacon.core.manifest import BeaconManifest
from beacon.warehouse import WarehouseValidator
```

## Rationale

**Why reference instead of duplicate:**
- **DRY principle** - Don't repeat standards across projects
- **Single source of truth** - Global standards apply universally
- **Automatic updates** - Changes to global standards apply automatically
- **Consistency** - Same patterns across all projects

## Implementation

In project AGENTS.md, simply reference the global standards:
```markdown
Follow the global Python standards from the user's AGENTS.md context
```

## Consequences

**Positive:**
- No duplication of standards
- Automatic consistency with other projects
- Reduced maintenance burden

**Negative:**
- External contributors may not have access to global standards
- Requires context loading to work properly

## Future Consideration

If this project becomes open source with external contributors, may need to inline the Python standards for clarity.
