# Python Language Context

Standards and patterns for Python development.

**Last Updated:** 2026-03-06

---

## Type Annotations

**Rule:** Use primitive types when available (`list` not `List`).

**Rule:** Only quote type annotations for forward references or circular imports.

**Read:** [Common annotation mistakes](~/.agentic-context/knowledge/languages/python/lessons/quoted-type-annotations.md)

---

## Pydantic vs Dataclass

**Rule:** Use Pydantic BaseModel as default for data carriers (internal and external).

**Rule:** Use dataclass only for service classes that hold state and methods.

**Read:** [When to use Pydantic vs dataclass](~/.agentic-context/knowledge/languages/python/decisions/pydantic-vs-dataclass.md)

---

## Exception Handling

**Rule:** Never use bare `except:` clauses - always specify exception types.

**Rule:** Use targeted try-except blocks for specific operations.

**See:** [Exception handling patterns](~/.agentic-context/knowledge/languages/python/lessons/exception-handling.md)

---

## Import Patterns

**Rule:** Use explicit imports, avoid wildcard imports (`from x import *`).

**Rule:** Leave `__init__.py` minimal or empty for most packages.
