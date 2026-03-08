# Decision: Settings Module Structure and Naming Conventions

**Date:** 2026-03-08  
**Status:** Accepted  
**Context:** Agentic Beacon configuration management structure

## Decision

1. Use `settings.py` as the module name for configuration management instead of `config.py`
2. Separate all custom exceptions into a dedicated `exceptions.py` module
3. Use "settings" terminology consistently (e.g., `WarehouseSettings`, `BeaconSettings`, `SettingsReader`)

## Rationale

### Using settings.py

1. **Semantic clarity**: "Settings" better represents application configuration vs "config" which could refer to files, objects, or processes
2. **Industry convention**: Pydantic Settings documentation and examples use "settings" as the standard naming
3. **Python ecosystem alignment**: Django, FastAPI, and other frameworks use `settings.py` for application configuration
4. **Consistency**: Using "settings" throughout (module name, class names, variables) creates a coherent API

### Separate exceptions.py Module

1. **Single source of truth**: All exception classes in one location makes them easy to find and maintain
2. **Avoid circular imports**: Separating exceptions from business logic prevents import cycles
3. **Better IDE support**: IDEs can better autocomplete and navigate exception hierarchies when centralized
4. **Cleaner imports**: `from beacon.core.exceptions import ValidationError` is clearer than importing from settings/service modules
5. **Python conventions**: Standard library and major frameworks use this pattern

## Module Structure

```
libs/beacon/src/beacon/core/
├── settings.py       # Settings models, readers, and writers
├── exceptions.py     # Custom exception hierarchy
└── __init__.py
```

## Settings Pattern

```python
# settings.py - Settings objects act as readers and writers

class WarehouseSettings(BaseSettings):
    """Warehouse connection settings from config.toml."""
    warehouse: WarehouseConfig
    
    @classmethod
    def from_path(cls, local_path: str) -> "WarehouseSettings":
        """Create settings from path and write to file."""
        # Validates, writes TOML, then loads via BaseSettings
        ...
    
    def to_toml(self, path: Path) -> None:
        """Write settings to TOML file."""
        ...

class BeaconSettings(BaseModel):
    """Beacon artifact dependencies from beacon.yaml."""
    artifacts: ArtifactsConfig
    
    @classmethod
    def from_yaml(cls, path: Path) -> "BeaconSettings":
        """Load settings from YAML file."""
        ...
    
    def to_yaml(self, path: Path) -> None:
        """Write settings to YAML file."""
        ...

# Helper function for validation
def validate_beacon_directory(base_dir: str = ".") -> Path:
    """Validate .agentic-beacon directory exists."""
    ...
```

## Usage: No Separate Reader/Writer Classes

Settings objects handle their own reading and writing:

```python
# Write settings
warehouse = WarehouseSettings.from_path("/path/to/warehouse")
beacon = BeaconSettings(artifacts=ArtifactsConfig(knowledge=["test.md"]))
beacon.to_yaml(".agentic-beacon/beacon.yaml")

# Read settings
warehouse = WarehouseSettings()  # Pydantic reads from config.toml automatically
beacon = BeaconSettings.from_yaml(".agentic-beacon/beacon.yaml")
```

**Rationale:** Pydantic Settings already handles reading configuration from files. We don't need separate Reader/Writer classes - the settings objects themselves are sufficient.

## Exception Hierarchy

```python
# exceptions.py
class BeaconError(Exception):
    """Base class for all Beacon errors."""
    pass

class ConfigurationError(BeaconError):
    """Base class for configuration errors."""
    pass

class ValidationError(ConfigurationError):
    """Raised when validation fails."""
    pass

class YAMLParseError(ConfigurationError):
    """Raised when YAML parsing fails."""
    pass

class TOMLParseError(ConfigurationError):
    """Raised when TOML parsing fails."""
    pass

class DirectoryNotFoundError(ConfigurationError):
    """Raised when .agentic-beacon directory not found."""
    pass

class WarehouseValidationError(ConfigurationError):
    """Raised when warehouse structure validation fails."""
    pass
```

## Usage Examples

```python
from beacon.core.settings import WarehouseSettings, BeaconSettings, ArtifactsConfig
from beacon.core.exceptions import ValidationError, ConfigurationError

# Writing settings
warehouse = WarehouseSettings.from_path("/path/to/warehouse")
beacon = BeaconSettings(artifacts=ArtifactsConfig(knowledge=["test.md"]))
beacon.to_yaml(".agentic-beacon/beacon.yaml")

# Reading settings
warehouse = WarehouseSettings()  # Auto-loads from config.toml
beacon = BeaconSettings.from_yaml(".agentic-beacon/beacon.yaml")

# Error handling
try:
    beacon_settings = BeaconSettings.from_yaml("beacon.yaml")
except ValidationError as e:
    logger.error(f"Invalid configuration: {e}")
```

## Benefits

- **Consistency**: "Settings" used throughout the codebase
- **Type safety**: Pydantic models provide automatic validation
- **Clear errors**: Dedicated exception hierarchy with meaningful error messages
- **Maintainability**: Easy to find all exceptions and settings-related code
- **Testability**: Simple to mock exceptions and test error handling

## Related Patterns

- Use Pydantic BaseSettings for TOML configuration with file source customization
- Manual YAML parsing with Pydantic validation for custom structures (beacon.yaml)
- Field validators for data integrity checks
- Clear separation between settings objects (data) and reader/writer classes (operations)
