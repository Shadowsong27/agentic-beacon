# Python Standards

Python-specific conventions for all Python projects.

---

## Type Annotations

**Brief:** All function signatures must have type annotations. Use primitive types, not the `typing` module where possible.

```python
# Correct
def process(items: list[str]) -> dict[str, int]:
    ...

# Avoid
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]:
    ...
```

Use `X | None` over `Optional[X]` (Python 3.10+).

---

## Data Models

**Brief:** Use Pydantic `BaseModel` for data carriers. Use `@dataclass` for service/logic classes only.

```python
# Data carrier — use Pydantic
class UserProfile(BaseModel):
    name: str
    email: str
    age: int | None = None

# Service class — use dataclass
@dataclass
class UserService:
    repo: UserRepository
    emailer: EmailService
```

---

## Dependency Management

**Brief:** Use `uv` for all dependency management. Do not use `pip` directly in projects.

```bash
uv add requests          # add a dependency
uv add --dev pytest      # add a dev dependency
uv sync                  # install all dependencies
```

---

## Linting & Formatting

**Brief:** Use `ruff` for both linting and formatting. No `flake8`, `black`, or `isort`.

```bash
ruff check .     # lint
ruff format .    # format
```

---

## Error Handling

**Brief:** Raise specific exceptions. Never catch bare `Exception` unless re-raising.

```python
# Correct
try:
    result = fetch_data(url)
except requests.HTTPError as e:
    raise DataFetchError(f"Failed to fetch {url}") from e

# Avoid
try:
    result = fetch_data(url)
except Exception:
    pass
```

---

## Imports

**Brief:** Standard library → third-party → local. `ruff` enforces this automatically.

No wildcard imports (`from module import *`).
