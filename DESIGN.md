# ascii-motion: design

Take an image, replicate it accurately in text characters, and animate that smoothly.
Two things drive every decision: how faithfully the characters reproduce the image,
and how smooth the animation is. The build is ordered to nail accuracy first, then
smoothness, then the AI passes that make the motion meaningful.

## Status

Day 3 of 7. Done: the accuracy engine (an image becomes a character grid with a
coverage-calibrated ramp, area-average sampling, aspect correction, and an edge pass)
and the web canvas animator that renders the frame model and assembles it on screen.

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

## Smoothness: the web animator (Day 2-3, done)

`web/` renders the frame model on a canvas and assembles it on screen. Three decisions
carry the smoothness:

- Glyph atlas, not fillText: every distinct glyph is drawn once into an offscreen
  canvas, and each frame blits sprites with drawImage. A 120x70 grid is 8400 cells, and
  calling fillText that many times per frame stutters; drawImage from an atlas does not.
  Spaces are skipped, which is most of a light image.
- Real clock, not frame counting: the reveal is driven by requestAnimationFrame with
  the actual elapsed time, so the easing is identical on a 60Hz and a 144Hz display
  rather than running faster on the quicker screen. The loop stops scheduling once every
  cell has settled, so an idle page costs nothing.
- devicePixelRatio scaling so the text stays crisp on retina screens, capped at 2x to
  bound the fill cost.

The reveal itself: each cell gets a normalized start offset by mode (wipe, radial,
scatter, rows), eased with easeOutCubic, fading in while sliding up a few pixels so the
grid reads as assembling itself. The pure math (easing, the per-mode delay, time to
progress) lives in `web/anim.js` and is unit tested in Node, separate from the DOM glue
in `web/app.js`. The page loads a bundled sample and accepts any frame .json the CLI
produces.

Default look is ink-on-paper in the warm palette, which matches the engine's
darkness-to-density calibration (a dark image area is dense ink) and the rest of the
portfolio. Edge shimmer and a depth-aware parallax come once segmentation lands.

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
- [x] Day 2-3: web canvas animator (smoothness)
- [ ] Day 4: video and frame morphing
- [ ] Day 5: AI segmentation and depth for subject-aware motion
- [ ] Day 6: accuracy polish (DoG edges, dithering, color, SSIM check)
- [ ] Day 7: web app and gallery
