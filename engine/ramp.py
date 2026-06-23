"""Glyph-coverage-calibrated brightness ramp.

The accuracy of character art comes down to one thing: matching a cell's darkness to
a glyph of the same ink density. A hand-guessed ramp like " .:-=+*#%@" is only roughly
ordered and unevenly spaced, so midtones drift. Instead this measures the real ink
coverage of every candidate glyph in the actual render font and maps darkness to the
glyph with the nearest measured coverage. That keeps tones faithful.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# A wide printable set. The order here does not matter; coverage is measured and the
# set is re-sorted. Backslash and quotes are included as real density steps.
DEFAULT_CHARSET = (
    " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
)


@dataclass
class Ramp:
    chars: list[str]      # glyphs sorted light -> dark
    coverage: np.ndarray  # matching ink coverage in [0, 1], ascending

    def char_for_darkness(self, darkness: float) -> str:
        """Pick the glyph whose ink coverage is closest to the wanted darkness."""
        idx = int(np.argmin(np.abs(self.coverage - darkness)))
        return self.chars[idx]

    def map_darkness(self, darkness: np.ndarray) -> np.ndarray:
        """Vectorized lookup: darkness grid in [0,1] -> indices into chars.

        Coverage is ascending, so searchsorted finds the insertion point and we then
        snap to whichever of the two neighbors is actually closer.
        """
        pos = np.searchsorted(self.coverage, darkness)
        pos = np.clip(pos, 1, len(self.coverage) - 1)
        left = self.coverage[pos - 1]
        right = self.coverage[pos]
        closer_left = (darkness - left) <= (right - darkness)
        return np.where(closer_left, pos - 1, pos)


def build_ramp(font_path: str, font_size: int = 24, charset: str = DEFAULT_CHARSET) -> Ramp:
    font = ImageFont.truetype(font_path, font_size)
    ascent, descent = font.getmetrics()
    cell_h = ascent + descent
    cell_w = max(1, int(round(font.getlength("M"))))

    cover = []
    for ch in charset:
        img = Image.new("L", (cell_w, cell_h), color=255)  # white cell
        ImageDraw.Draw(img).text((0, 0), ch, fill=0, font=font)  # black ink
        # Coverage = average darkness over the cell, so a denser glyph scores higher.
        cover.append(1.0 - np.asarray(img, dtype=np.float64).mean() / 255.0)

    cov = np.asarray(cover)
    order = np.argsort(cov)  # light (low coverage) to dark (high coverage)
    chars = [charset[i] for i in order]
    cov = cov[order]

    # Normalize so the lightest glyph maps to 0 and the densest to 1. Without this the
    # ramp never reaches pure white (space has tiny nonzero coverage from anti-aliasing)
    # or true black, and the image looks washed out.
    lo, hi = cov[0], cov[-1]
    if hi > lo:
        cov = (cov - lo) / (hi - lo)
    return Ramp(chars=chars, coverage=cov)


def cell_aspect(font_path: str, font_size: int = 24) -> float:
    """Width / height of one character cell. Monospace cells are tall (~0.6), so the
    row count must be scaled by this or the picture comes out vertically stretched."""
    font = ImageFont.truetype(font_path, font_size)
    ascent, descent = font.getmetrics()
    return font.getlength("M") / (ascent + descent)
