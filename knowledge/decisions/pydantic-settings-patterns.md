# Decision: Pydantic Settings Patterns for Configuration Management

**Date:** 2026-03-08  
**Status:** Accepted  
**Context:** Configuration management standardization

## Decision

Use Pydantic Settings patterns for all configuration management in Agentic Beacon, following established best practices for type-safe, validated configuration.

## Rationale

1. **Type safety**: Pydantic provides automatic validation and type coercion
2. **Environment variable support**: Built-in env var support with prefixes and nested delimiters
3. **TOML configuration support**: First-class TOML file loading via `TomlConfigSettingsSource`
4. **Validation**: Field validators ensure data integrity before application startup
5. **Documentation**: Self-documenting via Field descriptions
6. **Testing**: Easy to test with fixtures and mock settings

## Key Patterns

### 1. Inherit from BaseSettings for File-Based Configuration

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class WarehouseSettings(BaseSettings):
    """Warehouse connection settings from config.toml."""
    
    model_config = SettingsConfigDict(
        toml_file=".agentic-beacon/config.toml",
        extra="ignore",  # Forward compatibility
    )
    
    warehouse: WarehouseConfig
```

### 2. Customize Settings Sources

Control where settings come from (TOML files, environment variables, etc.):

```python
from pydantic_settings import TomlConfigSettingsSource

@classmethod
def settings_customise_sources(
    cls,
    settings_cls: type[BaseSettings],
    init_settings: PydanticBaseSettingsSource,
    env_settings: PydanticBaseSettingsSource,
    dotenv_settings: PydanticBaseSettingsSource,
    file_secret_settings: PydanticBaseSettingsSource,
) -> tuple[PydanticBaseSettingsSource, ...]:
    """Use TOML file as the sole configuration source."""
    return (
        TomlConfigSettingsSource(
            settings_cls,
            toml_file=cls.model_config.get("toml_file"),
        ),
    )
```

### 3. Nested Configuration Models

Use Pydantic BaseModel for nested configuration sections:

```python
class WarehouseConfig(BaseModel):
    """Warehouse configuration section."""
    
    local_path: str = Field(..., description="Absolute path to local warehouse")
    
    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, v: str) -> str:
        """Validate and normalize path."""
        if not v or not v.strip():
            raise ValueError("local_path cannot be empty")
        
        path = Path(v).expanduser().resolve()
        if not path.is_absolute():
            raise ValueError("local_path must be an absolute path")
        
        return str(path)

class WarehouseSettings(BaseSettings):
    """Root settings model."""
    warehouse: WarehouseConfig
```

### 4. Field Validators for Data Integrity

```python
from pydantic import field_validator

@field_validator("artifact_path")
@classmethod
def validate_artifact_path(cls, v: str) -> str:
    """Ensure artifact paths are relative and normalized."""
    path = Path(v)
    if path.is_absolute():
        raise ValueError("Artifact paths must be relative")
    return str(path)
```

### 5. Manual Parsing for Custom Structures

For configurations with non-standard structures (like beacon.yaml with grouped artifacts), use manual parsing with Pydantic validation:

```python
class BeaconSettings(BaseModel):
    """Custom structure requiring manual parsing."""
    
    artifacts: ArtifactsConfig
    
    @classmethod
    def from_yaml(cls, path: Path) -> "BeaconSettings":
        """Manual YAML parsing with validation."""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        # Validate structure
        if "artifacts" not in data:
            raise ValidationError("Missing required 'artifacts' section")
        
        # Use Pydantic for validation
        return cls(**data)
```

## Benefits

- **Type-safe configuration** with automatic validation
- **Clear error messages** when configuration is invalid
- **Easy to test** with fixtures
- **Supports both file-based and programmatic configuration**
- **Forward-compatible** with `extra="ignore"`
- **Self-documenting** through Field descriptions
- **IDE support** with type hints

## Adaptations for Beacon

1. **beacon.yaml custom structure**: Manual parsing for non-standard YAML structure (artifacts grouped by type)
2. **No environment variables for local settings**: config.toml is project-specific, not environment-driven
3. **Separate validator classes**: BeaconYamlValidator provides structure validation independently

## Example: Complete Settings Flow

```python
# 1. Define settings
class WarehouseSettings(BaseSettings):
    model_config = SettingsConfigDict(toml_file="config.toml")
    warehouse: WarehouseConfig

# 2. Load settings
reader = SettingsReader()
warehouse_settings, beacon_settings = reader.load()

# 3. Access validated data
warehouse_path = warehouse_settings.warehouse.local_path  # Type-safe!
artifacts = beacon_settings.artifacts.knowledge  # list[str]
```

## Related Decisions

- [Settings Module Structure and Naming Conventions](./settings-module-structure.md)
