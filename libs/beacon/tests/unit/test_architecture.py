"""Architecture tests for beacon package layering.

These tests enforce the domain-layer design from specs/layered-architecture/spec.md.
"""

import ast
from pathlib import Path

import pytest

BEACON_SRC = Path(__file__).parents[2] / "src" / "beacon"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_py_files_under(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def _parse_file(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


def _is_docstring_node(node: ast.AST) -> bool:
    """Return True if node is a module-level docstring Expr."""
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


# ---------------------------------------------------------------------------
# TC1: Six domain packages exist
# ---------------------------------------------------------------------------


def test_six_domains_exist():
    """Exactly six domain directories shall exist."""
    domains_dir = BEACON_SRC / "domains"
    expected = {
        "warehouse",
        "setup",
        "adoption",
        "distribution",
        "contribution",
        "artifact",
    }
    actual = {
        d.name
        for d in domains_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    }
    assert actual == expected, (
        f"Missing or extra domain dirs: {expected.symmetric_difference(actual)}"
    )


# ---------------------------------------------------------------------------
# TC2: No stray top-level modules
# ---------------------------------------------------------------------------


def test_no_stray_top_level_modules():
    """The only .py file directly under beacon/ shall be __init__.py."""
    allowed = {"__init__.py"}
    for path in BEACON_SRC.iterdir():
        if path.is_file() and path.suffix == ".py":
            assert path.name in allowed, f"Disallowed top-level file: {path.name}"


# ---------------------------------------------------------------------------
# TC3: core/ has no domain/cli imports
# ---------------------------------------------------------------------------


def test_core_has_no_domain_imports():
    """Files under core/ shall not import from domains or cli."""
    core_dir = BEACON_SRC / "core"
    bad_prefixes = ("beacon.domains.", "beacon.cli")
    for path in _all_py_files_under(core_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(bad_prefixes), (
                    f"{path}: core/ must not import from {mod}"
                )


# ---------------------------------------------------------------------------
# TC4: utils/ has no higher-layer imports
# ---------------------------------------------------------------------------


def test_utils_has_no_higher_layer_imports():
    """Files under utils/ shall not import from domains, cli, or core."""
    utils_dir = BEACON_SRC / "utils"
    bad_prefixes = ("beacon.domains.", "beacon.cli", "beacon.core.")
    for path in _all_py_files_under(utils_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(bad_prefixes), (
                    f"{path}: utils/ must not import from {mod}"
                )


# ---------------------------------------------------------------------------
# TC5: Cross-domain imports use top-level
# ---------------------------------------------------------------------------


def test_cross_domain_imports_use_top_level():
    """Domains shall import from each other's top-level packages, not deep paths."""
    domains_dir = BEACON_SRC / "domains"
    for path in _all_py_files_under(domains_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if not mod.startswith("beacon.domains."):
                    continue
                # e.g. beacon.domains.artifact.skill -> depth 4
                parts = mod.split(".")
                if len(parts) > 4:
                    pytest.fail(
                        f"{path}: cross-domain import must use top-level, not {mod}"
                    )


# ---------------------------------------------------------------------------
# TC6: No underscore cross-module imports
# ---------------------------------------------------------------------------


def test_no_underscore_cross_module_imports():
    """No function, class, or constant imported cross-module starts with underscore."""
    for path in _all_py_files_under(BEACON_SRC):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name.startswith("_"):
                        pytest.fail(
                            f"{path}: importing underscore-prefixed name "
                            f"'{alias.name}' from {node.module}"
                        )


# ---------------------------------------------------------------------------
# TC7: Empty __init__.py files
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TC8: CLI handlers have no I/O
# ---------------------------------------------------------------------------


def test_cli_handlers_have_no_io():
    """
    Parse every function in beacon/cli/**/*.py decorated with @click.command()
    or @<group>.command(); assert the body contains no forbidden I/O calls.
    """
    cli_dir = BEACON_SRC / "cli"
    if not cli_dir.exists():
        pytest.skip("cli/ directory does not exist yet")

    # Forbidden bare names (e.g. open(), run())
    forbidden_names = {
        "open",
        "run",  # subprocess.run
        "walk",  # os.walk
        "glob",  # glob.glob
        "rmtree",  # shutil.rmtree
        "copy",  # shutil.copy
        "copy2",  # shutil.copy2
        "copytree",  # shutil.copytree
        "copyfile",  # shutil.copyfile
    }

    # Forbidden attribute chains regardless of receiver name
    # e.g. any_path.read_text(), shutil.rmtree(...)
    forbidden_attrs = {
        # pathlib / os methods
        "read_text",
        "write_text",
        "unlink",
        "mkdir",
        "rmdir",
        "rglob",
        "glob",
        # yaml / tomllib
        "load",
        # shutil
        "rmtree",
        "copy",
        "copy2",
        "copytree",
        "copyfile",
    }

    # Forbidden two-element chains (module.function)
    forbidden_module_attrs = {
        ("subprocess", "run"),
        ("yaml", "load"),
        ("tomllib", "load"),
        ("shutil", "rmtree"),
        ("shutil", "copy"),
        ("shutil", "copy2"),
        ("shutil", "copytree"),
        ("shutil", "copyfile"),
        ("glob", "glob"),
        ("os", "walk"),
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
                # Check for bare names: open(), run(), walk(), etc.
                if (
                    isinstance(child.func, ast.Name)
                    and child.func.id in forbidden_names
                ):
                    pytest.fail(
                        f"{path}::{func_name}: forbidden call to {child.func.id}()"
                    )
                elif isinstance(child.func, ast.Attribute):
                    # Build attribute chain: e.g. ["Path", "write_text"] or ["shutil", "rmtree"]
                    attr_chain = []
                    obj = child.func
                    while isinstance(obj, ast.Attribute):
                        attr_chain.append(obj.attr)
                        obj = obj.value
                    if isinstance(obj, ast.Name):
                        attr_chain.append(obj.id)
                    attr_chain.reverse()

                    # Check tail attribute regardless of receiver (e.g. any_path.read_text())
                    if attr_chain[-1] in forbidden_attrs:
                        pytest.fail(
                            f"{path}::{func_name}: forbidden call to "
                            f"{'.'.join(attr_chain)}()"
                        )

                    # Check module.function pairs
                    if len(attr_chain) == 2:
                        pair = (attr_chain[0], attr_chain[1])
                        if pair in forbidden_module_attrs:
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


# ---------------------------------------------------------------------------
# TC9: No free functions in cli/
# ---------------------------------------------------------------------------


def test_cli_has_no_free_functions():
    """
    beacon/cli/**/*.py shall contain only Click command/group handlers and
    module-level imports. No free helper functions.
    """
    cli_dir = BEACON_SRC / "cli"
    if not cli_dir.exists():
        pytest.skip("cli/ directory does not exist yet")

    def _is_click_decorated(node: ast.FunctionDef) -> bool:
        """Check if function has a click.command or click.group decorator."""
        for d in node.decorator_list:
            if isinstance(d, ast.Call):
                func = d.func
                if isinstance(func, ast.Attribute) and func.attr in (
                    "command",
                    "group",
                ):
                    return True
                if isinstance(func, ast.Name) and func.id in ("command", "group"):
                    return True
        return False

    for path in _all_py_files_under(cli_dir):
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not _is_click_decorated(node):
                pytest.fail(
                    f"{path}: free function '{node.name}' is not allowed in cli/. "
                    f"Move helpers to the domain layer."
                )
