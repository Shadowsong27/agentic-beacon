#!/usr/bin/env python3
"""Generate an SVG screenshot of the abc adopt TUI.

Usage:
    python scripts/screenshot_tui.py [output_path]

Defaults to docs/screenshots/adopt-tui.svg.
"""

import asyncio
import sys
from pathlib import Path

# Resolve repo root
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "libs/beacon/src"))

OUTPUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else REPO_ROOT / "docs/screenshots/adopt-tui.svg"
)

STARTER_WAREHOUSE = Path("/Users/shadowsong/Code/oss/agentic-beacon-starter-warehouse")


def _build_demo_candidates():
    from beacon.adopt import AdoptCandidate

    return [
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/global.md",
            description="Global Engineering Standards",
        ),
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/python.md",
            description="Python Coding Standards",
        ),
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/typescript.md",
            description="TypeScript Coding Standards",
        ),
        AdoptCandidate(
            artifact_type="skills",
            path="skills/code-review/",
            description="Perform a structured code review covering correctness, readability, security, and test coverage",
        ),
        AdoptCandidate(
            artifact_type="skills",
            path="skills/generate-tests/",
            description="Generate comprehensive unit and integration tests for a given function, module, or feature",
        ),
        AdoptCandidate(
            artifact_type="skills",
            path="skills/record-knowledge/",
            description="Systematically capture decisions, lessons, and facts into the project knowledge base",
        ),
        AdoptCandidate(
            artifact_type="knowledge",
            path="knowledge/engineering",
            description="Trunk-Based Development",
        ),
    ]


async def _capture():
    from beacon.adopt import _ADOPT_CSS, _DOCS_BASE, _SECTION_META
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import Footer, Header, Static, Tree

    _ARTIFACT_ICONS: dict[str, str] = {
        "contexts": "📄",
        "skills": "🔧",
        "knowledge": "📚",
        "agents": "🤖",
    }

    def _leaf_label(path: str, selected: bool, commits_ago: int | None = None) -> str:
        checkbox = "[bold cyan]\\[x][/bold cyan]" if selected else "[dim]\\[ ][/dim]"
        label = f"{checkbox} [cyan]{path}[/cyan]"
        if commits_ago is not None:
            plural = "s" if commits_ago != 1 else ""
            label += (
                f" [dim yellow]\\[added {commits_ago} commit{plural} ago][/dim yellow]"
            )
        return label

    candidates = _build_demo_candidates()

    class _ScreenshotApp(App[None]):
        CSS = _ADOPT_CSS
        TITLE = "Agentic Beacon"
        SUB_TITLE = "Artifact Adoption"
        BINDINGS = [
            Binding("ctrl+s", "screenshot", "Screenshot"),
        ]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            yield Static("", id="meta-panel")
            yield Tree("root", id="tree")
            yield Static("", id="desc-panel")
            yield Footer()

        def on_mount(self) -> None:
            self.theme = "catppuccin-mocha"
            meta = self.query_one("#meta-panel", Static)
            meta.update(
                "  [dim]project:[/dim] [bold]my-project[/bold]"
                "   │   [dim]warehouse:[/dim] [bold]starter-warehouse[/bold]"
                "   │   [dim]7 unadopted[/dim]  [dim]0 adopted[/dim]"
            )
            self._build_tree()
            self.call_after_refresh(self._do_screenshot)

        def _build_tree(self) -> None:
            tree = self.query_one("#tree", Tree)
            tree.root.remove_children()
            tree.show_root = False
            tree.root.expand()

            by_type: dict[str, list] = {}
            for c in candidates:
                by_type.setdefault(c.artifact_type, []).append(
                    (c.path, c.description, False, None, False)
                )

            def _build_knowledge_subtree(
                parent_node, items, depth_prefix: str = ""
            ) -> None:
                direct = []
                subgroups: dict[str, list] = {}
                for full_path, desc, selected, commits_ago_val, orig_adopted in items:
                    rel = full_path[len("knowledge/") :]
                    if depth_prefix:
                        rel = rel[len(depth_prefix) + 1 :]
                    slash_idx = rel.find("/")
                    if slash_idx == -1:
                        direct.append(
                            (
                                full_path,
                                rel,
                                desc,
                                selected,
                                commits_ago_val,
                                orig_adopted,
                            )
                        )
                    else:
                        group = rel[:slash_idx]
                        subgroups.setdefault(group, []).append(
                            (full_path, desc, selected, commits_ago_val, orig_adopted)
                        )
                for (
                    full_path,
                    name,
                    desc,
                    selected,
                    commits_ago_val,
                    _orig_adopted,
                ) in sorted(direct, key=lambda x: x[1]):
                    parent_node.add_leaf(
                        _leaf_label(name, selected, commits_ago_val),
                        data={
                            "path": full_path,
                            "display_name": name,
                            "desc": desc,
                            "selected": selected,
                        },
                    )
                for group_name in sorted(subgroups.keys()):
                    sub_prefix = (
                        group_name
                        if not depth_prefix
                        else f"{depth_prefix}/{group_name}"
                    )
                    sub_node = parent_node.add(
                        f"[dim white]{group_name}/[/dim white]",
                        expand=True,
                        data={"folder": group_name},
                    )
                    _build_knowledge_subtree(
                        sub_node, subgroups[group_name], sub_prefix
                    )

            for atype in ["contexts", "skills", "knowledge", "agents"]:
                type_items = by_type.get(atype, [])
                if not type_items:
                    continue
                icon = _ARTIFACT_ICONS.get(atype, "📂")
                section_desc, docs_path = _SECTION_META.get(atype, ("", ""))
                docs_url = f"{_DOCS_BASE}/{docs_path}" if docs_path else ""
                docs_link = (
                    f"  [dim][link={docs_url}]docs ↗[/link][/dim]" if docs_url else ""
                )
                section_label = (
                    f"[bold white]{icon} {atype}[/bold white]"
                    f"  [dim]{section_desc}[/dim]"
                    f"{docs_link}"
                )
                folder = tree.root.add(
                    section_label,
                    expand=True,
                    data={"docs_url": docs_url, "section": atype},
                )
                if atype == "knowledge":
                    _build_knowledge_subtree(folder, type_items)
                else:
                    for (
                        path,
                        desc,
                        selected,
                        commits_ago_val,
                        _orig_adopted,
                    ) in type_items:
                        short = path.split("/")[-1] if "/" in path else path
                        folder.add_leaf(
                            _leaf_label(short, selected, commits_ago_val),
                            data={
                                "path": path,
                                "display_name": short,
                                "desc": desc,
                                "selected": selected,
                            },
                        )

        async def _do_screenshot(self) -> None:
            svg = self.export_screenshot()
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(svg)
            print(f"Screenshot saved to {OUTPUT}")
            self.exit()

    app = _ScreenshotApp()
    await app.run_async(headless=True)


if __name__ == "__main__":
    asyncio.run(_capture())
