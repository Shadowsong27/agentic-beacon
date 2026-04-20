"""Architecture tests enforcing the layered-architecture spec.

These tests validate the four-layer package structure, dependency direction,
bounded contexts, CLI thinness, utility eligibility, and naming conventions.
"""

import ast
from pathlib import Path

import pytest

BEACON_SRC = Path(__file__).parents[2] / "src" / "beacon"

# Expected six bounded-context domains
EXPECTED_DOMAINS = {
    "warehouse",
    "setup",
    "adoption",
    "distribution",
    "contribution",
    "artifact",
}


def _all_py_files_under(*paths: Path) -> list[Path]:
    files = []
    for path in paths:
        if path.exists():
            files.extend(sorted(path.rglob("*.py")))
    return files


def _parse_file(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _is_docstring_node(node: ast.AST) -> bool:
    """Return True if node is a module-level docstring expression."""
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


def _get_imported_names(node: ast.ImportFrom) -> list[str]:
    """Return the actual names imported (handling aliases)."""
    return [alias.name for alias in node.names]


# ─── TC1: Six domains exist ────────────────────────────────────────────


def test_six_domains_exist():
    """Assert beacon/domains/ contains exactly six subpackages matching the spec."""
    domains_dir = BEACON_SRC / "domains"
    assert domains_dir.exists(), "domains/ directory must exist"

    actual = {
        p.name
        for p in domains_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    }
    assert actual == EXPECTED_DOMAINS, f"Expected {EXPECTED_DOMAINS}, got {actual}"

    for name in EXPECTED_DOMAINS:
        init = domains_dir / name / "__init__.py"
        assert init.exists(), f"domains/{name}/__init__.py must exist"


# ─── TC2: No stray top-level modules ───────────────────────────────────


def test_no_stray_top_level_modules():
    """The only .py files directly under beacon/ shall be __init__.py and cli.py."""
    allowed = {"__init__.py", "cli.py"}
    for path in BEACON_SRC.iterdir():
        if path.is_file() and path.suffix == ".py":
            assert path.name in allowed, f"Disallowed top-level file: {path.name}"


# ─── TC3: core/ has no domain/cli imports ──────────────────────────────


def test_core_has_no_domain_imports():
    """Parse every beacon/core/**/*.py and assert no imports from domains or cli.

    Note: core/cli/ is excluded because it contains CLI handlers that will move
    to beacon/cli/ in PR 7; CLI handlers are allowed to import from domains.
    Tripwire: once beacon/cli/ exists, core/cli/ must no longer exist.
    """
    cli_dir = BEACON_SRC / "cli"
    core_cli_dir = BEACON_SRC / "core" / "cli"
    # Tripwire: when beacon/cli/ is created, core/cli/ should be gone
    if cli_dir.exists() and core_cli_dir.exists():
        pytest.fail(
            "Both beacon/cli/ and beacon/core/cli/ exist. "
            "PR 7 should have removed core/cli/."
        )

    core_dir = BEACON_SRC / "core"
    for path in _all_py_files_under(core_dir):
        # Skip CLI handlers — they live under core/cli/ temporarily (PR 7 moves them)
        if "core/cli/" in str(path):
            continue
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("beacon.domains") or module.startswith(
                    "beacon.cli"
                ):
                    pytest.fail(f"{path}: forbidden import from {module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("beacon.domains") or alias.name.startswith(
                        "beacon.cli"
                    ):
                        pytest.fail(f"{path}: forbidden import {alias.name}")


# ─── TC4: utils/ has no higher-layer imports ───────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason="will pass after PR 1 (artifact) moves agents/skills out, since those currently import from beacon.core",
)
def test_utils_has_no_higher_layer_imports():
    """Parse every beacon/utils/**/*.py and assert no imports from cli, domains, or core."""
    utils_dir = BEACON_SRC / "utils"
    for path in _all_py_files_under(utils_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    module.startswith("beacon.cli")
                    or module.startswith("beacon.domains")
                    or module.startswith("beacon.core")
                ):
                    pytest.fail(f"{path}: forbidden import from {module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name.startswith("beacon.cli")
                        or alias.name.startswith("beacon.domains")
                        or alias.name.startswith("beacon.core")
                    ):
                        pytest.fail(f"{path}: forbidden import {alias.name}")


# ─── TC5: Cross-domain imports use top-level modules ───────────────────


def test_cross_domain_imports_use_top_level():
    """
    For each `from beacon.domains.<A>.<...>` import in beacon/domains/<B>/**,
    assert <...> has depth exactly 1 (a module directly under domains/<A>/).
    Only enforced for cross-domain imports (<A> != <B>); same-domain deep
    imports are allowed.
    """
    domains_dir = BEACON_SRC / "domains"
    for path in _all_py_files_under(domains_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        # Determine which domain this file belongs to
        path_parts = path.relative_to(domains_dir).parts
        owning_domain = path_parts[0] if path_parts else ""

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if not module.startswith("beacon.domains."):
                continue
            # module is like "beacon.domains.artifact.agent" or "beacon.domains.artifact.sub.foo"
            parts = module.split(".")
            imported_domain = parts[2] if len(parts) >= 3 else ""
            # Skip same-domain imports — deep imports within a domain are allowed
            if imported_domain == owning_domain:
                continue
            # Cross-domain imports must reference a top-level module (depth == 1)
            if len(parts) != 4:
                pytest.fail(
                    f"{path}: cross-domain import '{module}' must reference a top-level module "
                    f"directly under domains/{imported_domain}/, not a deeper internal"
                )


# ─── TC6: No underscore-prefixed cross-module imports ──────────────────


@pytest.mark.xfail(
    strict=True,
    reason="will pass after each PR renames its _-prefixed functions (PRs 1-7)",
)
def test_no_underscore_cross_module_imports():
    """
    For every `from beacon.*` import across the package, assert the imported
    name does not begin with '_'.
    """
    for path in _all_py_files_under(BEACON_SRC):
        # Skip __init__.py files (they're checked separately)
        if path.name == "__init__.py":
            continue
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if not module.startswith("beacon."):
                continue
            for name in _get_imported_names(node):
                if name.startswith("_"):
                    pytest.fail(
                        f"{path}: imports underscore-prefixed name '{name}' from {module}"
                    )


# ─── TC7: Empty __init__.py files ──────────────────────────────────────


def test_init_files_are_empty():
    """
    Parse every __init__.py under beacon/{cli,domains,core,utils}/ and assert
    its AST body contains only a module docstring or is empty.
    """
    for subdir in ("cli", "domains", "core", "utils"):
        for path in (BEACON_SRC / subdir).rglob("__init__.py"):
            tree = _parse_file(path)
            if tree is None:
                continue

            # Filter out docstring nodes from the body
            non_docstring = [node for node in tree.body if not _is_docstring_node(node)]
            assert not non_docstring, (
                f"{path}: __init__.py must contain only a module docstring, "
                f"found {len(non_docstring)} other statement(s)"
            )


# ─── TC8: CLI handlers have no I/O ─────────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason="will pass after PR 7 (CLI thinning)",
)
def test_cli_handlers_have_no_io():
    """
    Parse every function in beacon/cli/**/*.py decorated with @click.command()
    or @<group>.command(); assert the body contains no calls to open(),
    Path.write_text, Path.read_text, yaml.load, tomllib.load, subprocess.run.
    """
    cli_dir = BEACON_SRC / "cli"
    if not cli_dir.exists():
        pytest.skip("cli/ directory does not exist yet")

    forbidden_names = {
        "open",
        "write_text",
        "read_text",
        "load",  # yaml.load, tomllib.load
        "run",  # subprocess.run
    }
    forbidden_attrs = {
        ("Path", "write_text"),
        ("Path", "read_text"),
        ("yaml", "load"),
        ("tomllib", "load"),
        ("subprocess", "run"),
    }

    def _is_click_command_decorator(node: ast.expr) -> bool:
        """Heuristic: is this decorator a click command registration?"""
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                return func.attr == "command"
            if isinstance(func, ast.Name):
                return func.id == "command"
        return False

    def _check_node_for_io(node: ast.AST, path: Path, func_name: str) -> None:
        """Walk a function body looking for forbidden I/O calls."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check for open(), Path.write_text(), etc.
                if (
                    isinstance(child.func, ast.Name)
                    and child.func.id in forbidden_names
                ):
                    pytest.fail(
                        f"{path}::{func_name}: forbidden call to {child.func.id}()"
                    )
                elif isinstance(child.func, ast.Attribute):
                    attr_chain = []
                    obj = child.func
                    while isinstance(obj, ast.Attribute):
                        attr_chain.append(obj.attr)
                        obj = obj.value
                    if isinstance(obj, ast.Name):
                        attr_chain.append(obj.id)
                    attr_chain.reverse()
                    if len(attr_chain) == 2:
                        pair = (attr_chain[0], attr_chain[1])
                        if pair in forbidden_attrs:
                            pytest.fail(
                                f"{path}::{func_name}: forbidden call to "
                                f"{'.'.join(attr_chain)}()"
                            )

    for path in _all_py_files_under(cli_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                is_handler = any(
                    _is_click_command_decorator(d) for d in node.decorator_list
                )
                if is_handler:
                    _check_node_for_io(node, path, node.name)
