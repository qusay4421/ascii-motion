"""Optional monocular depth estimation.

Where segmentation gives a flat subject-vs-background split, a depth map gives a
continuous near-to-far value per pixel, which lets the animator parallax the scene:
near characters shift more than far ones as a slow virtual camera pans, so a still
image gains a sense of space. Uses MiDaS small as an ONNX model run on onnxruntime,
free and offline. The model is ~64MB and is not vendored; see scripts/get-depth-model.sh.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "..", "assets", "midas_small.onnx")
# ImageNet normalization the MiDaS small model was trained with.
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)


def depth_map(image_path: str, model_path: str | None = None) -> np.ndarray:
    """Return a full-resolution depth map in [0, 1], where 1 is nearest.

    onnxruntime is imported lazily so the core engine has no hard dependency on it.
    """
    import onnxruntime as ort

    path = model_path or os.environ.get("ASCII_MOTION_DEPTH_MODEL") or DEFAULT_MODEL
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"depth model not found at {path}. Run scripts/get-depth-model.sh or set "
            "ASCII_MOTION_DEPTH_MODEL."
        )
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name

    bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    inp = (cv2.resize(rgb, (256, 256)) - _MEAN) / _STD
    inp = np.transpose(inp, (2, 0, 1))[None].astype(np.float32)

    out = sess.run(None, {name: inp})[0][0]
    depth = cv2.resize(out, (w, h))
    # MiDaS returns relative inverse depth; min-max to [0,1] so larger means nearer.
    lo, hi = float(depth.min()), float(depth.max())
    if hi > lo:
        depth = (depth - lo) / (hi - lo)
    return depth


def depth_to_cells(depth: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Area-average a full-resolution depth map down to a rows x cols grid in [0,1]."""
    return cv2.resize(depth.astype(np.float32), (cols, rows), interpolation=cv2.INTER_AREA)
