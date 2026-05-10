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


def _is_click_command_decorator(node: ast.expr) -> bool:
    """Return True if *node* is a @<group>.command() or @click.command() decorator."""
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr == "command"
        if isinstance(func, ast.Name):
            return func.id == "command"
    return False


def _collect_domain_symbols(tree: ast.AST) -> set[str]:
    """Return the local names of all symbols imported from beacon.domains.*.

    Handles both forms:
    - ``from beacon.domains.foo import bar`` → symbol ``bar`` (or asname)
    - ``import beacon.domains.foo`` → symbol ``beacon`` (root) and ``foo`` (leaf)
    - ``import beacon.domains.foo as alias`` → symbol ``alias``
    """
    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("beacon.domains."):
                for alias in node.names:
                    symbols.add(alias.asname if alias.asname else alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("beacon.domains."):
                    if alias.asname:
                        symbols.add(alias.asname)
                    else:
                        # ``import beacon.domains.foo`` — the local name is the
                        # dotted root accessible as ``beacon.domains.foo.bar()``,
                        # but callers use the first segment; record all segments
                        # so attribute-call detection can match any prefix.
                        parts = alias.name.split(".")
                        for part in parts:
                            symbols.add(part)
    return symbols


def _count_domain_calls_in_handler(
    func: ast.FunctionDef, domain_symbols: set[str]
) -> int:
    """Count ast.Call nodes that directly invoke a domain-imported symbol.

    Counts two call forms:
    - Direct call: ``symbol(...)`` where symbol ∈ domain_symbols
    - Attribute call: ``alias.method(...)`` where alias ∈ domain_symbols
      (covers ``import beacon.domains.foo as alias; alias.bar()``)

    Method calls on plain instances are NOT counted separately; instantiation +
    method chain = one logical domain interaction.
    """
    count = 0
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            func_node = node.func
            if isinstance(func_node, ast.Name) and func_node.id in domain_symbols:
                count += 1
            elif (
                isinstance(func_node, ast.Attribute)
                and isinstance(func_node.value, ast.Name)
                and func_node.value.id in domain_symbols
            ):
                count += 1
    return count


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
# TC9b: every CLI handler invokes at most ONE domain function
#
# A "domain call" is a direct call (ast.Name node) to a symbol imported from
# beacon.domains.*. Method calls on domain instances are NOT counted separately
# (instantiation + subsequent method chain = one logical interaction).
#
# Known violations pending cleanup — each entry is (filename, handler_name).
# To clean a waiver: fix the handler, remove its entry, and re-run the tests.
# ---------------------------------------------------------------------------

_TC9B_WAIVERS: set[tuple[str, str]] = {
    # TODO: wrap multiple setup-wiring calls in a single domain function (PER-120 follow-up)
    ("sync.py", "sync"),
    ("sync.py", "status"),
    # TODO: wrap discovery + commit + cleanup into a single adopt domain function
    ("adoption.py", "adopt"),
}


def test_cli_handlers_have_one_domain_call():
    """Each click command handler in beacon/cli/**/*.py shall invoke at most one
    domain function per handler body (direct call to a beacon.domains.* symbol).
    """
    cli_dir = BEACON_SRC / "cli"
    if not cli_dir.exists():
        pytest.skip("cli/ directory does not exist yet")

    failures: list[str] = []

    for path in _all_py_files_under(cli_dir):
        tree = _parse_file(path)
        if tree is None:
            continue

        domain_symbols = _collect_domain_symbols(tree)
        filename = path.name

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not any(_is_click_command_decorator(d) for d in node.decorator_list):
                continue

            if (filename, node.name) in _TC9B_WAIVERS:
                continue

            count = _count_domain_calls_in_handler(node, domain_symbols)
            if count > 1:
                failures.append(
                    f"{path}::{node.name}: {count} domain calls — max 1 allowed "
                    f"(wrap extras into a single domain function)"
                )

    # Verify no waived file or handler has disappeared (stale waivers are noise)
    cli_files_by_name = {p.name: p for p in _all_py_files_under(cli_dir)}
    for waived_file, waived_handler in _TC9B_WAIVERS:
        waived_path = cli_files_by_name.get(waived_file)
        if waived_path is None:
            failures.append(
                f"stale waiver: {waived_file}::{waived_handler} — "
                f"file no longer exists; remove the waiver"
            )
            continue
        waived_tree = _parse_file(waived_path)
        handler_found = waived_tree is not None and any(
            isinstance(node, ast.FunctionDef)
            and node.name == waived_handler
            and any(_is_click_command_decorator(d) for d in node.decorator_list)
            for node in ast.walk(waived_tree)
        )
        if not handler_found:
            failures.append(
                f"stale waiver: {waived_file}::{waived_handler} no longer exists; "
                f"remove the waiver"
            )

    if failures:
        pytest.fail("\n" + "\n".join(failures))


# ---------------------------------------------------------------------------
# TC9c: negative test — multi-domain-call violation IS detectable
# ---------------------------------------------------------------------------


def test_cli_multi_domain_call_violation_is_detected():
    """TC9c: the TC9b rule must flag a synthetic handler with two domain calls.

    This proves the detection logic actually works; if the rule is broken the
    negative test fails first, making the breakage obvious.
    """
    import textwrap

    src = textwrap.dedent("""\
        import click
        from beacon.domains.setup.wiring import create_beacon_template
        from beacon.domains.warehouse.validator import WarehouseValidator

        @click.command()
        def bad_handler():
            validator = WarehouseValidator()
            create_beacon_template(some_path)
    """)
    tree = ast.parse(src, filename="<synthetic>")
    domain_symbols = _collect_domain_symbols(tree)

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(_is_click_command_decorator(d) for d in node.decorator_list):
            continue
        count = _count_domain_calls_in_handler(node, domain_symbols)
        if count > 1:
            violations.append(f"{node.name}: {count} domain calls")

    assert violations, (
        "TC9c FAILED: multi-domain-call violation was NOT detected — "
        "the architecture rule in test_cli_handlers_have_one_domain_call is broken"
    )


# ---------------------------------------------------------------------------
# TC9d: negative test — ``import ... as alias`` form is also detected
# ---------------------------------------------------------------------------


def test_cli_multi_domain_call_via_import_as_is_detected():
    """TC9d: the TC9b rule must flag a handler using two ``import X as alias`` calls.

    This proves the attribute-call detection path works; a handler that does
    ``import beacon.domains.foo as foo; foo.bar(); foo.baz()`` must be caught.
    """
    import textwrap

    src = textwrap.dedent("""\
        import click
        import beacon.domains.warehouse.connector as connector
        import beacon.domains.setup.wiring as wiring

        @click.command()
        def bad_handler():
            connector.connect_to_warehouse(proj, wh)
            wiring.create_beacon_template(some_path)
    """)
    tree = ast.parse(src, filename="<synthetic>")
    domain_symbols = _collect_domain_symbols(tree)

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(_is_click_command_decorator(d) for d in node.decorator_list):
            continue
        count = _count_domain_calls_in_handler(node, domain_symbols)
        if count > 1:
            violations.append(f"{node.name}: {count} domain calls")

    assert violations, (
        "TC9d FAILED: import-as alias domain-call violation was NOT detected — "
        "_collect_domain_symbols or _count_domain_calls_in_handler is broken"
    )


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
