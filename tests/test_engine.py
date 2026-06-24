"""Objective correctness tests for the conversion engine.

These do not eyeball a photo; they feed synthetic images with known structure and
assert the engine reproduces it: a gradient must map to a monotonic density of glyphs,
oriented lines must pick the matching directional glyph, and the grid must keep the
image's aspect once the tall character cell is accounted for.

Run from the repo root:
    python tests/test_engine.py        (standalone, no pytest needed)
    python -m pytest tests/
"""

import os
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import build_ramp, to_grid  # noqa: E402
from engine.ramp import cell_aspect  # noqa: E402

FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "DejaVuSansMono.ttf")
RAMP = build_ramp(FONT)


def _write(img: np.ndarray) -> str:
    path = tempfile.mktemp(suffix=".png")
    cv2.imwrite(path, img)
    return path


def test_ramp_is_sorted_light_to_dark():
    assert RAMP.coverage[0] == 0.0 and RAMP.coverage[-1] == 1.0
    assert np.all(np.diff(RAMP.coverage) >= 0), "coverage must be non-decreasing"
    # The lightest glyph is whitespace; the densest is a heavy block-like char.
    assert RAMP.chars[0] == " "
    assert RAMP.char_for_darkness(1.0) in "@MWNQB#g0&%"


def test_map_darkness_matches_scalar_lookup():
    for d in (0.0, 0.1, 0.37, 0.5, 0.8, 1.0):
        grid = np.array([[d]])
        idx = RAMP.map_darkness(grid)[0, 0]
        assert RAMP.chars[idx] == RAMP.char_for_darkness(d)


def test_gradient_maps_to_monotonic_density():
    # Black on the left, white on the right. Left cells must be denser than right.
    grad = np.tile(np.linspace(0, 255, 256, dtype=np.uint8), (64, 1))
    grid = to_grid(_write(cv2.cvtColor(grad, cv2.COLOR_GRAY2BGR)), cols=60, font_path=FONT, edges=False)
    cover = np.array([[RAMP.coverage[RAMP.chars.index(ch)] for ch in row] for row in grid.chars])
    left = cover[:, : grid.cols // 3].mean()
    right = cover[:, -grid.cols // 3 :].mean()
    assert left > right + 0.3, f"left {left:.2f} should be much denser than right {right:.2f}"


def test_solid_images_hit_the_ramp_ends():
    black = to_grid(_write(np.zeros((80, 80, 3), np.uint8)), cols=20, font_path=FONT, edges=False)
    white = to_grid(_write(np.full((80, 80, 3), 255, np.uint8)), cols=20, font_path=FONT, edges=False)
    assert all(ch == RAMP.chars[-1] for row in black.chars for ch in row), "solid black -> densest glyph"
    assert all(ch == " " for row in white.chars for ch in row), "solid white -> space"


def test_vertical_line_uses_vertical_glyph():
    img = np.zeros((200, 200, 3), np.uint8)
    img[:, 95:105] = 255  # vertical white bar
    grid = to_grid(_write(img), cols=60, font_path=FONT, edges=True)
    edge_chars = [grid.chars[r][c] for r in range(grid.rows) for c in range(grid.cols) if grid.is_edge[r, c]]
    assert edge_chars, "an edge should be detected"
    assert edge_chars.count("|") >= len(edge_chars) * 0.6, f"vertical line should be mostly '|': {set(edge_chars)}"


def test_horizontal_line_uses_horizontal_glyph():
    img = np.zeros((200, 200, 3), np.uint8)
    img[95:105, :] = 255  # horizontal white bar
    grid = to_grid(_write(img), cols=60, font_path=FONT, edges=True)
    edge_chars = [grid.chars[r][c] for r in range(grid.rows) for c in range(grid.cols) if grid.is_edge[r, c]]
    assert edge_chars, "an edge should be detected"
    assert edge_chars.count("-") >= len(edge_chars) * 0.6, f"horizontal line should be mostly '-': {set(edge_chars)}"


def test_aspect_correction_keeps_proportions():
    # A square image must produce fewer rows than cols, scaled by the cell aspect.
    grid = to_grid(_write(np.full((300, 300, 3), 128, np.uint8)), cols=100, font_path=FONT, edges=False)
    expected = 100 * cell_aspect(FONT)
    assert abs(grid.rows - expected) <= 2, f"rows {grid.rows} should be near {expected:.1f}"


def test_mask_to_cells_downsamples_to_subject_grid():
    from engine import mask_to_cells

    # Left half subject, right half background; must survive the reduction to the grid.
    mask = np.zeros((100, 100), np.float32)
    mask[:, :50] = 1.0
    cells = mask_to_cells(mask, rows=10, cols=10)
    assert cells.shape == (10, 10)
    assert cells[:, :5].all() and not cells[:, 5:].any()


def test_subject_flows_into_grid_and_json():
    from engine import to_grid, to_json
    import json

    mask = np.zeros((120, 120), np.float32)
    mask[:, :60] = 1.0
    grid = to_grid(_write(np.full((120, 120, 3), 128, np.uint8)), cols=40, font_path=FONT,
                   edges=False, subject=mask)
    assert grid.is_subject is not None and grid.is_subject.shape == (grid.rows, grid.cols)
    model = json.loads(to_json(grid))
    assert "subject" in model and len(model["subject"]) == grid.rows * grid.cols


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
