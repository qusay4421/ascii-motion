"""Optional subject segmentation.

This is the "understand the boundaries" step: a U2-Net model (via rembg) separates the
foreground subject from the background, so the animator can move the subject on its own
instead of applying one uniform effect to the whole frame. The model is free and runs
offline, but it is a heavy dependency, so it is imported lazily and only used when the
caller asks for it.
"""

from __future__ import annotations

import cv2
import numpy as np


def subject_mask(image_path: str, model: str = "u2net") -> np.ndarray:
    """Return a full-resolution mask in [0, 1] where 1 is the subject.

    Imports rembg lazily so the core engine has no hard dependency on it.
    """
    from PIL import Image
    from rembg import remove, new_session

    img = Image.open(image_path).convert("RGB")
    mask = remove(img, session=new_session(model), only_mask=True)
    return np.asarray(mask, dtype=np.float32) / 255.0


def mask_to_cells(mask: np.ndarray, rows: int, cols: int, thresh: float = 0.5) -> np.ndarray:
    """Area-average a full-resolution mask down to a rows x cols boolean subject grid.

    Averaging before thresholding (rather than nearest-sampling one pixel per cell)
    keeps the subject outline stable instead of jagged at the grid resolution.
    """
    small = cv2.resize(mask.astype(np.float32), (cols, rows), interpolation=cv2.INTER_AREA)
    return small >= thresh
