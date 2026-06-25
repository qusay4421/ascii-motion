from .ramp import Ramp, build_ramp, cell_aspect, DEFAULT_CHARSET
from .convert import Grid, to_grid
from .render import to_text, to_png, to_json
from .segment import mask_to_cells  # subject_mask is imported lazily (heavy rembg dep)
from .measure import ssim, fidelity

__all__ = [
    "Ramp", "build_ramp", "cell_aspect", "DEFAULT_CHARSET",
    "Grid", "to_grid",
    "to_text", "to_png", "to_json",
    "mask_to_cells",
    "ssim", "fidelity",
]
