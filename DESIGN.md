# ascii-motion: design

Take an image, replicate it accurately in text characters, and animate that smoothly.
Two things drive every decision: how faithfully the characters reproduce the image,
and how smooth the animation is. The build is ordered to nail accuracy first, then
smoothness, then the AI passes that make the motion meaningful.

## Status

Day 6 of 7. Done: the accuracy engine (image to a faithful character grid), a measurable SSIM fidelity score, the web
canvas animator that assembles it on screen, and U2-Net segmentation so the subject
animates independently of the background, a measurable SSIM fidelity score, and DoG
edges. Remaining: depth-based parallax, video morphing, and the upload web app.

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

## AI boundaries: segmentation (Day 5, done)

This is where "understand the boundaries" earns its place. A free, local U2-Net model
(via rembg, no API) produces a foreground mask, which `engine/segment.py` reduces to a
per-cell subject flag carried in the frame model. The animator then treats the subject
and background differently: the background assembles first, the figure emerges on top,
and once settled the subject drifts on its own with a tiny phase-shifted offset while
the background stays put. That is the segmentation paying off, the figure moves
independently instead of one uniform effect sweeping the whole frame.

It is optional and lazily imported, so the core engine has no hard dependency on the
heavy model. `cli.py --segment` runs it. Verified on a portrait: the mask is a clean
silhouette, and a character-domain overlay confirms the subject cells trace the figure.
The mask-to-grid reduction and the JSON round-trip are unit tested; the reveal phasing
is tested in `web/anim.js`.

Still ahead here: a depth model (Depth-Anything / MiDaS) for a parallax that uses real
scene depth rather than a flat subject-vs-background split.

## Accuracy polish and a fidelity score (Day 6, done)

Accuracy now has a number. `engine/measure.py` scores how closely the chosen glyphs
reproduce the source tones using SSIM (the standard perceptual image metric), comparing
the target darkness the converter computed against the true ink density of the glyph it
picked, cell for cell. Edge cells are neutralized so the score reflects the tone layer,
not the deliberately tone-deviating edge glyphs. `cli.py --measure` prints it.

The score makes the central accuracy claim measurable: the coverage-calibrated ramp
reproduces a portrait at SSIM 0.986, against 0.925 for a naive ramp that assumes evenly
spaced glyph densities. That 0.06 gap is the payoff of measuring real glyph coverage
instead of guessing the order, and it is now a regression-testable number rather than a
claim.

`--edge-method dog` adds difference-of-Gaussians edges as an alternative to Sobel. DoG
responds to thin lines and suppresses smooth shading, so contours come out cleaner;
direction still comes from the Sobel gradient. Tests cover SSIM identity and its drop
under noise, the gradient fidelity, that the calibrated ramp beats the naive one, and
DoG line detection.

Still ahead: optional ordered dithering and gamma controls.

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
- [x] Day 5a: AI segmentation for subject-aware motion (U2-Net)
- [ ] Day 5b: depth model (Depth-Anything) for parallax
- [x] Day 6: accuracy polish (DoG edges + SSIM fidelity score)
- [ ] Day 7: web app and gallery
