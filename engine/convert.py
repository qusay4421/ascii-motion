"""Image to character grid.

Pipeline, each step chosen for replication accuracy:
  1. perceptual luminance (not a flat channel average)
  2. area-average downsample to the character grid (every output cell is the true mean
     of the pixels it covers, so brightness is faithful and not point-sampled)
  3. aspect correction for the tall monospace cell
  4. optional auto-contrast to use the full tonal range
  5. darkness -> glyph via the coverage-calibrated ramp
  6. an edge pass that replaces fill glyphs with directional line glyphs (| / - \\)
     where the image has strong structure, which is what makes it read as drawn
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .ramp import Ramp, build_ramp, cell_aspect

# Edge orientation glyphs, indexed by a 4-way quantization of the gradient angle.
EDGE_GLYPHS = ["|", "/", "-", "\\"]


@dataclass
class Grid:
    chars: list[list[str]]   # rows of single-character strings
    color: np.ndarray        # (rows, cols, 3) uint8 average RGB per cell
    is_edge: np.ndarray      # (rows, cols) bool, True where an edge glyph was used
    is_subject: np.ndarray | None = None  # (rows, cols) bool, set when segmentation runs

    @property
    def rows(self) -> int:
        return len(self.chars)

    @property
    def cols(self) -> int:
        return len(self.chars[0]) if self.chars else 0


def _luminance(bgr: np.ndarray) -> np.ndarray:
    # Rec. 601 perceptual weights; matches how the eye sees brightness far better than
    # a flat mean, which would make blue look as bright as green.
    b, g, r = bgr[..., 0], bgr[..., 1], bgr[..., 2]
    return 0.114 * b + 0.587 * g + 0.299 * r


def _grid_shape(img_h: int, img_w: int, cols: int, aspect: float) -> tuple[int, int]:
    # rows so that rendered (rows*cell_h) / (cols*cell_w) matches the image aspect.
    rows = max(1, int(round(cols * (img_h / img_w) * aspect)))
    return rows, cols


def _edge_directions(gray: np.ndarray, rows: int, cols: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-cell edge strength and a 4-way glyph index from the Sobel gradient."""
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    # Average gradients down to the grid before taking the angle, so each cell gets the
    # dominant local edge direction instead of one noisy pixel's.
    gxc = cv2.resize(gx, (cols, rows), interpolation=cv2.INTER_AREA)
    gyc = cv2.resize(gy, (cols, rows), interpolation=cv2.INTER_AREA)
    magc = cv2.resize(mag, (cols, rows), interpolation=cv2.INTER_AREA)

    angle = np.degrees(np.arctan2(gyc, gxc)) % 180.0  # gradient orientation, 0..180
    # Gradient is perpendicular to the edge. Bin so a horizontal gradient (0 deg) gives
    # a vertical bar '|', a vertical gradient (90) gives '-', and the diagonals map to
    # '/' and '\\'. Verified against synthetic lines and the portrait render.
    bin_idx = (((angle + 22.5) % 180.0) / 45.0).astype(int) % 4
    return magc, bin_idx


def to_grid(
    image_path: str,
    cols: int = 120,
    font_path: str = "assets/DejaVuSansMono.ttf",
    font_size: int = 24,
    edges: bool = True,
    edge_strength: float = 0.18,
    auto_contrast: bool = True,
    ramp: Ramp | None = None,
    subject: np.ndarray | None = None,
) -> Grid:
    bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    if ramp is None:
        ramp = build_ramp(font_path, font_size)

    img_h, img_w = bgr.shape[:2]
    rows, cols = _grid_shape(img_h, img_w, cols, cell_aspect(font_path, font_size))

    gray = _luminance(bgr).astype(np.float32)
    small = cv2.resize(gray, (cols, cols and rows), interpolation=cv2.INTER_AREA)

    norm = small / 255.0
    if auto_contrast:
        lo, hi = float(norm.min()), float(norm.max())
        if hi > lo:
            norm = (norm - lo) / (hi - lo)

    darkness = 1.0 - norm  # dark pixels need dense glyphs
    idx = ramp.map_darkness(darkness)
    chars = [[ramp.chars[idx[r, c]] for c in range(cols)] for r in range(rows)]

    is_edge = np.zeros((rows, cols), dtype=bool)
    if edges:
        magc, bin_idx = _edge_directions(gray, rows, cols)
        thresh = magc.max() * edge_strength
        for r in range(rows):
            for c in range(cols):
                if magc[r, c] >= thresh and thresh > 0:
                    chars[r][c] = EDGE_GLYPHS[bin_idx[r, c]]
                    is_edge[r, c] = True

    color = cv2.cvtColor(
        cv2.resize(bgr, (cols, rows), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB
    )

    is_subject = None
    if subject is not None:
        # A precomputed full-res mask is reduced to the grid here so the heavy
        # segmentation import stays out of the core converter.
        from .segment import mask_to_cells
        is_subject = mask_to_cells(subject, rows, cols)

    return Grid(chars=chars, color=color, is_edge=is_edge, is_subject=is_subject)
