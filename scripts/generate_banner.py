#!/usr/bin/env python3
"""Generate the agentic-beacon README banner as a terminal-style ASCII diagram PNG."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).parent.parent
OUT = REPO_ROOT / "agentic-beacon-banner.png"

# ── Catppuccin Mocha palette ──────────────────────────────────────────────────
BG = (24, 24, 37)  # base
SURFACE = (30, 30, 46)  # surface0
OVERLAY = (49, 50, 68)  # overlay0
CRUST = (17, 17, 27)  # crust
CYAN = (137, 220, 235)  # sky
GREEN = (166, 227, 161)  # green
MAUVE = (203, 166, 247)  # mauve
PEACH = (250, 179, 135)  # peach
TEXT = (205, 214, 244)  # text
SUBTEXT = (147, 153, 178)  # subtext0
DIM = (88, 91, 112)  # overlay0 dimmer

W, H = 1200, 480
PAD = 56
FONT_SIZE = 22
SMALL_SIZE = 18


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/Library/Fonts/Courier New.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_text(draw, x, y, text, font, color=TEXT):
    draw.text((x, y), text, font=font, fill=color)
    return y + font.size + 4


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    mono = load_font(FONT_SIZE)
    small = load_font(SMALL_SIZE)
    big = load_font(32)

    # ── top bar ───────────────────────────────────────────────────────────────
    d.rectangle([(0, 0), (W, 52)], fill=SURFACE)
    # traffic lights
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([(PAD + i * 28, 18), (PAD + i * 28 + 16, 34)], fill=col)
    title = "agentic-beacon — abc"
    tw = d.textlength(title, font=small)
    d.text(((W - tw) / 2, 16), title, font=small, fill=SUBTEXT)

    y = 80

    # ── title block ───────────────────────────────────────────────────────────
    d.text((PAD, y), "AGENTIC BEACON", font=big, fill=CYAN)
    tw2 = d.textlength("AGENTIC BEACON", font=big)
    d.text(
        (PAD + tw2 + 18, y + 6),
        "·  abc  ·  The package manager for AI coding agents",
        font=small,
        fill=SUBTEXT,
    )
    y += 52

    # ── separator ─────────────────────────────────────────────────────────────
    sep = "─" * 110
    d.text((PAD, y), sep, font=mono, fill=OVERLAY)
    y += 36

    # ── diagram ───────────────────────────────────────────────────────────────
    LX = PAD  # left box x
    CH = FONT_SIZE + 6  # line height

    lines = [
        # (text, [(start_char, color), ...])  — colored spans
        ("  warehouse/                           project/", [(2, DIM), (41, DIM)]),
        (
            "  ┌─────────────────────┐             ┌──────────────────────────────┐",
            [(2, OVERLAY), (45, OVERLAY)],
        ),
        (
            "  │  contexts/          │──abc sync──►│  AGENTS.md · opencode.json   │",
            [
                (2, DIM),
                (4, CYAN),
                (23, DIM),
                (24, SUBTEXT),
                (37, DIM),
                (39, GREEN),
                (70, DIM),
            ],
        ),
        (
            "  │  knowledge/         │──abc sync──►│  .agentic-beacon/artifacts/  │",
            [
                (2, DIM),
                (4, MAUVE),
                (23, DIM),
                (24, SUBTEXT),
                (37, DIM),
                (39, GREEN),
                (70, DIM),
            ],
        ),
        (
            "  │  skills/            │──abc sync──►│  .opencode/skills/           │",
            [
                (2, DIM),
                (4, PEACH),
                (23, DIM),
                (24, SUBTEXT),
                (37, DIM),
                (39, GREEN),
                (70, DIM),
            ],
        ),
        (
            "  │  agents/            │──abc sync──►│  ~/.claude/agents/           │",
            [
                (2, DIM),
                (4, SUBTEXT),
                (23, DIM),
                (24, SUBTEXT),
                (37, DIM),
                (39, GREEN),
                (70, DIM),
            ],
        ),
        (
            "  └─────────────────────┘             └──────────────────────────────┘",
            [(2, OVERLAY), (45, OVERLAY)],
        ),
        (
            "       ▲                                        │",
            [(7, OVERLAY), (48, OVERLAY)],
        ),
        (
            "       └──────────── abc contribute ◄───────────┘",
            [(7, SUBTEXT), (21, CYAN), (36, SUBTEXT)],
        ),
    ]

    for line, spans in lines:
        # collect (start, color) sorted
        sorted_spans = sorted(spans, key=lambda s: s[0])
        for i, (start, color) in enumerate(sorted_spans):
            end = sorted_spans[i + 1][0] if i + 1 < len(sorted_spans) else len(line)
            segment = line[start:end]
            if segment:
                d.text(
                    (LX + d.textlength(line[:start], font=mono), y),
                    segment,
                    font=mono,
                    fill=color,
                )
        y += CH

    img.save(OUT, "PNG", optimize=True)
    print(f"Saved {OUT}  ({OUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
