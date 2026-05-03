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


def test_expected_domains_exist():
    """Exactly five domain directories shall exist (contribution removed)."""
    domains_dir = BEACON_SRC / "domains"
    expected = {
        "warehouse",
        "setup",
        "adoption",
        "distribution",
        "artifact",
    }
    actual = {
        d.name
        for d in domains_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        # Ignore stale pycache-only leftovers of deleted domain packages.
        and any(d.glob("*.py"))
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
    """Cross-domain imports shall not exceed depth 4 (beacon.domains.X.Y).

    Because __init__.py files must remain empty (no re-exports), imports
    frequently target submodules (e.g. beacon.domains.artifact.skill).
    The enforced rule is: module path may be at most 4 parts deep.
    """
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


# ---------------------------------------------------------------------------
# TC9b: cli/warehouse.py handlers have at most ONE domain call
# ---------------------------------------------------------------------------


def test_warehouse_cli_handlers_have_one_domain_call():
    """
    Each top-level click command function in cli/warehouse.py shall contain
    at most ONE call into a domains.* module (plus argument parsing and
    output formatting).
    """
    cli_file = BEACON_SRC / "cli" / "warehouse.py"
    tree = _parse_file(cli_file)
    assert tree is not None, f"Could not parse {cli_file}"

    def _is_click_command_decorator(node: ast.expr) -> bool:
        """Heuristic: is this decorator a click command registration?"""
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                return func.attr == "command"
            if isinstance(func, ast.Name):
                return func.id == "command"
        return False

    failures: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        is_handler = any(_is_click_command_decorator(d) for d in node.decorator_list)
        if not is_handler:
            continue

        domain_calls = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check for module.function pattern where module starts with domains
                func = child.func
                if isinstance(func, ast.Attribute):
                    # e.g. some_module.some_function()
                    # Walk up the attribute chain to find the module name
                    attr_chain = []
                    obj = func
                    while isinstance(obj, ast.Attribute):
                        attr_chain.append(obj.attr)
                        obj = obj.value
                    if isinstance(obj, ast.Name):
                        attr_chain.append(obj.id)
                    attr_chain.reverse()
                    # Check if it's a domains import: domains.X.Y or beacon.domains.X.Y
                    if len(attr_chain) >= 2:
                        mod_name = ".".join(attr_chain[:-1])
                        if "domains" in mod_name:
                            domain_calls += 1

        if domain_calls > 1:
            failures.append(
                f"{cli_file}::{node.name}: has {domain_calls} domain calls, "
                f"max allowed is 1"
            )

    if failures:
        pytest.fail("\n" + "\n".join(failures))


# ---------------------------------------------------------------------------
# TC10: domains/ and core/ are Click/Rich/sys.exit-free
#
# Waivers below document known violations pending cleanup.
# Each entry is a relative path (from beacon/) → set of allowed breach types.
# Allowed breach types: "click", "rich", "sys.exit"
#
# To clean a file: remove its entry from _TC10_WAIVERS (or shrink the set).
# If a waiver disappears without a corresponding code fix, the test fails.
# If new code introduces a violation without a waiver, the test fails.
# ---------------------------------------------------------------------------

_TC10_WAIVERS: dict[str, set[str]] = {
    # TODO: extract interactive UX to CLI layer
    "domains/adoption/apply.py": {"click", "rich"},
    "domains/artifact/agent.py": {"click", "rich", "sys.exit"},
    "domains/artifact/skill.py": {"rich", "sys.exit"},
    "domains/distribution/upgrader.py": {"click"},
    "domains/setup/wiring.py": {"click", "rich"},
    "domains/warehouse/catalog.py": {"rich"},
}


def test_domains_and_core_are_cli_free():
    """domains/ and core/ shall not import click, rich, or call sys.exit.

    Violations are tracked in _TC10_WAIVERS above.  Files with a waiver are
    allowed to keep their current breach type(s); any *new* violation in a
    non-waived file (or a new breach type in a waived file) causes a failure.

    To clean up a violation: fix the code and remove the file from _TC10_WAIVERS
    (or remove just the breach type).  The test will then enforce the improvement
    permanently.
    """
    roots = [BEACON_SRC / "domains", BEACON_SRC / "core"]
    failures: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in _all_py_files_under(root):
            tree = _parse_file(path)
            if tree is None:
                continue

            rel = str(path.relative_to(BEACON_SRC))
            allowed = _TC10_WAIVERS.get(rel, set())

            found_click = False
            found_rich = False
            found_sys_exit = False

            for node in ast.walk(tree):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    if isinstance(node, ast.Import):
                        names = [alias.name.split(".")[0] for alias in node.names]
                    else:
                        names = [(node.module or "").split(".")[0]]
                    for top in names:
                        if top == "click":
                            found_click = True
                        elif top == "rich":
                            found_rich = True

                elif isinstance(node, ast.Call):
                    if (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "sys"
                        and node.func.attr == "exit"
                    ):
                        found_sys_exit = True

            if found_click and "click" not in allowed:
                failures.append(
                    f"{rel}: imports 'click' — move interactive UX to cli/ layer "
                    f"(or add waiver to _TC10_WAIVERS)"
                )
            if found_rich and "rich" not in allowed:
                failures.append(
                    f"{rel}: imports 'rich' — move display output to cli/ layer "
                    f"(or add waiver to _TC10_WAIVERS)"
                )
            if found_sys_exit and "sys.exit" not in allowed:
                failures.append(
                    f"{rel}: calls sys.exit() — raise an exception instead; "
                    f"CLI layer owns process exit (or add waiver to _TC10_WAIVERS)"
                )

    # Also verify no waived file has *disappeared* (stale waivers are noise)
    all_rel_paths = set()
    for root in roots:
        if root.exists():
            for path in _all_py_files_under(root):
                all_rel_paths.add(str(path.relative_to(BEACON_SRC)))

    for waived_path in _TC10_WAIVERS:
        if waived_path not in all_rel_paths:
            failures.append(
                f"_TC10_WAIVERS entry '{waived_path}' no longer exists — "
                f"remove the stale waiver"
            )

    if failures:
        pytest.fail("\n" + "\n".join(failures))
