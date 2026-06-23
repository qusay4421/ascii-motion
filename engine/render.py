"""Render a Grid to text, to a PNG preview, or to the JSON frame model the web
animator consumes."""

from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .convert import Grid


def to_text(grid: Grid) -> str:
    return "\n".join("".join(row) for row in grid.chars)


def to_png(
    grid: Grid,
    out_path: str,
    font_path: str = "assets/DejaVuSansMono.ttf",
    font_size: int = 24,
    color: bool = False,
    bg=(13, 13, 13),
    fg=(220, 220, 220),
) -> None:
    """Rasterize the character grid back to an image, the honest way to judge fidelity:
    if the PNG of the characters still reads as the photo, the replication is good."""
    font = ImageFont.truetype(font_path, font_size)
    ascent, descent = font.getmetrics()
    cell_h = ascent + descent
    cell_w = max(1, int(round(font.getlength("M"))))

    img = Image.new("RGB", (grid.cols * cell_w, grid.rows * cell_h), color=bg)
    draw = ImageDraw.Draw(img)
    for r in range(grid.rows):
        for c in range(grid.cols):
            ch = grid.chars[r][c]
            if ch == " ":
                continue
            fill = tuple(int(v) for v in grid.color[r, c]) if color else fg
            draw.text((c * cell_w, r * cell_h), ch, fill=fill, font=font)
    img.save(out_path)


def to_json(grid: Grid) -> str:
    """Compact frame model for the animator: one string of characters per row plus a
    flat color array and an edge mask. Rows-of-strings keeps the payload small and
    lets the front end address any cell by (row, col)."""
    model = {
        "rows": grid.rows,
        "cols": grid.cols,
        "chars": ["".join(row) for row in grid.chars],
        "color": grid.color.reshape(-1, 3).astype(int).tolist(),
        "edges": grid.is_edge.astype(int).flatten().tolist(),
    }
    return json.dumps(model, separators=(",", ":"))
