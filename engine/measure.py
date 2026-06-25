"""A fidelity score for the replication.

"Accurate" needs a number, not an opinion. This measures how closely the chosen glyphs
reproduce the source tones, cell for cell, with SSIM (structural similarity), the
standard perceptual image-comparison metric. It compares two darkness fields: the
target darkness the converter computed from the image, and the darkness actually
achieved by the glyphs it picked (each glyph's measured ink coverage). A score near 1
means the character art tracks the image's structure closely.
"""

from __future__ import annotations

import cv2
import numpy as np

from .convert import Grid
from .ramp import Ramp


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Mean SSIM between two single-channel arrays in [0, 255]. Gaussian-windowed,
    the usual 11x11 sigma 1.5, computed with blurs so it stays fast."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    k = (11, 11)
    s = 1.5
    mu_a = cv2.GaussianBlur(a, k, s)
    mu_b = cv2.GaussianBlur(b, k, s)
    mu_a2, mu_b2, mu_ab = mu_a * mu_a, mu_b * mu_b, mu_a * mu_b
    var_a = cv2.GaussianBlur(a * a, k, s) - mu_a2
    var_b = cv2.GaussianBlur(b * b, k, s) - mu_b2
    cov = cv2.GaussianBlur(a * b, k, s) - mu_ab
    smap = ((2 * mu_ab + C1) * (2 * cov + C2)) / ((mu_a2 + mu_b2 + C1) * (var_a + var_b + C2))
    return float(smap.mean())


def achieved_darkness(grid: Grid, ramp: Ramp) -> np.ndarray:
    """The darkness each chosen glyph actually contributes, from its measured coverage."""
    cov_by_char = {ch: ramp.coverage[i] for i, ch in enumerate(ramp.chars)}
    out = np.zeros((grid.rows, grid.cols), dtype=np.float64)
    for r in range(grid.rows):
        for c in range(grid.cols):
            out[r, c] = cov_by_char.get(grid.chars[r][c], 0.0)
    return out


def fidelity(grid: Grid, ramp: Ramp) -> float:
    """Tonal fidelity: SSIM between the target darkness and the true ink density of the
    glyph the grid actually chose, cell for cell.

    `ramp` supplies the reference (true, measured) coverage. Because the achieved value
    comes from grid.chars, a grid that picked glyphs by a worse-spaced ramp scores
    lower, which is what makes this a real accuracy measure. Edge cells are neutralized
    (set to the target) so the edge layer, which trades tone for line structure on
    purpose, does not distort the tonal score. Requires grid.darkness (to_grid sets it).
    """
    if grid.darkness is None:
        raise ValueError("grid has no darkness field; build it with to_grid")
    achieved = achieved_darkness(grid, ramp)
    if grid.is_edge is not None:
        achieved = np.where(grid.is_edge, grid.darkness, achieved)
    return ssim(grid.darkness * 255.0, achieved * 255.0)
