# ascii-motion: design

Take an image, replicate it accurately in text characters, and animate that smoothly.
Two things drive every decision: how faithfully the characters reproduce the image,
and how smooth the animation is. The build is ordered to nail accuracy first, then
smoothness, then the AI passes that make the motion meaningful.

## Status

Day 1 of 7. Done: the accuracy engine. An image becomes a character grid with a
coverage-calibrated brightness ramp, area-average sampling, aspect correction, and an
edge pass, exported to text, a PNG preview, and a JSON frame model.

## Accuracy: how the replication stays faithful (Day 1, done)

The pipeline (`engine/`) is built around one idea: match each cell's darkness to a
glyph of the same real ink density.

- Calibrated ramp (`ramp.py`): instead of trusting a hand-ordered string like
  " .:-=+*#%@", every candidate glyph is rendered in the actual font and its ink
  coverage is measured. Darkness then maps to the glyph with the nearest coverage, and
  the ramp is normalized so the lightest glyph is pure paper and the densest is full
  ink. This is what keeps midtones from drifting.
- Perceptual luminance: Rec. 601 weights, so brightness matches how the eye sees it
  rather than a flat channel average.
- Area-average downsampling: each output cell is the true mean of the pixels it
  covers (INTER_AREA), so tone is faithful and not point-sampled.
- Aspect correction: a monospace cell is about 0.6 as wide as it is tall, so the row
  count is scaled by the measured cell aspect or the picture comes out stretched.
- Edge pass (`convert.py`): Sobel gradients are averaged down to the grid, and where a
  cell sits on a strong edge its fill glyph is replaced by a directional line glyph
  (`|` `/` `-` `\`) chosen from the gradient angle. This is what makes the result read
  as drawn instead of dithered. Tests confirm a vertical line picks `|`, a horizontal
  line picks `-`, a gradient maps to a monotonic density, and solid black and white hit
  the ramp ends.
- Auto-contrast stretches the tonal range so a flat-exposure photo still uses the full
  ramp.

Outputs (`render.py`): the character text, a PNG that rasterizes the characters back to
an image (the honest fidelity check: if the PNG still reads as the photo, replication
is good), and a compact JSON frame model (rows of character strings plus per-cell color
and an edge mask) for the animator.

## Smoothness: the web animator (Day 2-3, TODO)

Render the frame model on a canvas, not the DOM. A grid of thousands of characters as
DOM nodes cannot animate at 60fps; drawing glyphs to a 2D canvas (or WebGL later) can.
The animator interpolates with requestAnimationFrame and an easing curve. First
animations: assemble-in (characters fade and settle into place), edge shimmer along the
contour glyphs, and a cursor reveal. Smoothness is the priority, so this stage is about
frame budget and easing, not feature count.

## Video and morphing (Day 4, TODO)

Accept a video or image sequence, convert each frame, and play them back with the
characters morphing between frames so motion stays smooth rather than flickering.

## AI boundaries (Day 5, TODO)

This is where "understand the boundaries" earns its place. A free, local segmentation
model (rembg / U2-Net, or Segment Anything) gives a subject mask, and a depth model
(Depth-Anything / MiDaS) gives a depth map. With those, the subject can move
independently of the background and the scene can parallax, so the animation means
something instead of being a uniform effect. All models are free and run offline.

## Accuracy polish (Day 6, TODO)

Difference-of-Gaussians edges for cleaner lines, optional ordered dithering, color and
gamma controls, and ramp tuning per font. Measured against the source with a structural
similarity check.

## Web app and gallery (Day 7, TODO)

Upload an image, get the animated character art in the browser, with a few presets. Tie
the look to the rest of the portfolio.

## Non-goals

- Real-time webcam conversion at high resolution (the per-frame cost is fine for video
  files but not a priority).
- A custom font renderer; the vendored DejaVu Sans Mono is enough.

## Roadmap

- [x] Day 1: accuracy engine (calibrated ramp, sampling, edges, PNG and JSON export)
- [ ] Day 2-3: web canvas animator (smoothness)
- [ ] Day 4: video and frame morphing
- [ ] Day 5: AI segmentation and depth for subject-aware motion
- [ ] Day 6: accuracy polish (DoG edges, dithering, color, SSIM check)
- [ ] Day 7: web app and gallery
