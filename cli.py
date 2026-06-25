"""Turn an image into character art.

    python cli.py portrait.jpg --width 140 --out out/portrait

Writes <out>.txt (the characters), <out>.png (a render to eyeball fidelity), and
<out>.json (the frame model for the web animator).
"""

import argparse
import os

from engine import to_grid, to_text, to_png, to_json, build_ramp, fidelity

FONT = os.path.join(os.path.dirname(__file__), "assets", "DejaVuSansMono.ttf")


def main() -> None:
    p = argparse.ArgumentParser(description="Image to character art")
    p.add_argument("image")
    p.add_argument("--width", type=int, default=120, help="output columns")
    p.add_argument("--out", default="out", help="output path prefix")
    p.add_argument("--no-edges", action="store_true", help="disable directional edge glyphs")
    p.add_argument("--color", action="store_true", help="color the PNG preview per cell")
    p.add_argument("--font-size", type=int, default=24)
    p.add_argument("--segment", action="store_true",
                   help="run U2-Net to tag subject vs background (needs rembg)")
    p.add_argument("--edge-method", choices=("sobel", "dog"), default="sobel",
                   help="edge detector: sobel, or dog for cleaner thin contours")
    p.add_argument("--measure", action="store_true",
                   help="print the SSIM tonal-fidelity score")
    args = p.parse_args()

    subject = None
    if args.segment:
        from engine.segment import subject_mask
        subject = subject_mask(args.image)

    ramp = build_ramp(FONT, args.font_size)
    grid = to_grid(args.image, cols=args.width, font_path=FONT,
                   font_size=args.font_size, edges=not args.no_edges,
                   edge_method=args.edge_method, subject=subject, ramp=ramp)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(f"{args.out}.txt", "w") as f:
        f.write(to_text(grid))
    with open(f"{args.out}.json", "w") as f:
        f.write(to_json(grid))
    to_png(grid, f"{args.out}.png", font_path=FONT, font_size=args.font_size, color=args.color)

    print(f"{grid.cols}x{grid.rows} cells -> {args.out}.txt, {args.out}.png, {args.out}.json")
    if args.measure:
        print(f"tonal fidelity (SSIM): {fidelity(grid, ramp):.3f}")


if __name__ == "__main__":
    main()
