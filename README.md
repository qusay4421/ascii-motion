# ascii-motion

Take an image, replicate it accurately in text characters, and (soon) animate it
smoothly in the browser. The focus is fidelity: matching each cell's darkness to a
glyph of the same real ink density, with directional line glyphs along edges so the
result reads as drawn rather than dithered.

This is day one of a longer build. The accuracy engine is done; the web animator,
video support, and AI subject/depth passes are on the roadmap in [DESIGN.md](DESIGN.md).

## What works today

- Image to character grid with a glyph-coverage-calibrated brightness ramp.
- Perceptual luminance, area-average sampling, and aspect correction for the tall
  monospace cell, so tone and proportions stay faithful.
- An edge pass that lays directional glyphs (`|` `/` `-` `\`) along strong edges.
- Outputs: the character text, a PNG that renders the characters back to an image (the
  honest way to judge fidelity), and a JSON frame model for the coming animator.

## Run

Requires Python 3.10+.

```sh
pip install -r requirements.txt
python cli.py path/to/image.jpg --width 140 --out out/image
# writes out/image.txt, out/image.png, out/image.json
```

Flags: `--width` columns, `--color` to color the PNG per cell, `--no-edges` to drop the
directional glyphs, `--font-size` for the preview scale.

## Animate it

The `web/` folder is a static page that renders a frame model on a canvas and assembles
it on screen (wipe, radial, scatter, or rows reveal). It ships with a sample, and you
can load any `.json` the CLI writes.

```sh
cd web
python3 -m http.server 8000   # then open http://localhost:8000
```

Smoothness comes from a glyph atlas (each character is drawn once, then blitted with
drawImage instead of thousands of fillText calls), a real-clock requestAnimationFrame
loop so the easing is the same on any refresh rate, and devicePixelRatio scaling for
crisp text. The animation math is unit tested with `node --test web/anim.test.mjs`.

## Test

```sh
python tests/test_engine.py        # or: python -m pytest tests/
```

Tests feed synthetic images with known structure and assert the engine reproduces it:
the brightness ramp is sorted by measured coverage, a gradient maps to a monotonic
density, oriented lines pick the matching glyph, solid tones hit the ramp ends, and the
grid keeps the image's aspect.

## Layout

```
engine/ramp.py      glyph-coverage-calibrated brightness ramp
engine/convert.py   image -> character grid (luminance, sampling, aspect, edges)
engine/render.py    grid -> text, PNG preview, JSON frame model
cli.py              command-line entry point
web/                static canvas animator (anim.js math is unit tested)
assets/             vendored DejaVu Sans Mono (see assets/FONT-LICENSE.txt)
tests/              objective correctness tests
DESIGN.md           design, accuracy notes, and the roadmap
```

## Font

The vendored font is DejaVu Sans Mono, a free font. See `assets/FONT-LICENSE.txt`.
