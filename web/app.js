// Browser glue: load a frame model, build a glyph atlas, and animate the character
// grid on a canvas. The smoothness ideas live here:
//   - render each unique glyph once into an offscreen atlas, then blit sprites with
//     drawImage instead of calling fillText thousands of times per frame
//   - drive everything off requestAnimationFrame with a real clock, so the easing is
//     frame-rate independent and does not speed up on a faster display
//   - scale the canvas by devicePixelRatio so text stays crisp
import { revealDelay, cellProgress, phasedDelay, parallaxOffset } from "./anim.js";

const PALETTE = { paper: "#f3efe6", ink: "#221f1c" }; // warm, ink-on-paper
const FONT_PX = 16;
const REVEAL = { stagger: 1.6, duration: 0.6 }; // seconds

const state = {
  model: null,
  atlas: null, // { canvas, w, h, index: Map<char, x> }
  delays: null, // Float32Array of normalized per-cell start offsets
  depth: null, // Float32Array of per-cell depth in [0,1], when present
  mode: "wipe",
  start: 0,
  mouse: { x: 0, y: 0 }, // normalized -0.5..0.5, nudges the parallax camera
};

const canvas = document.getElementById("stage");
const ctx = canvas.getContext("2d");
const dpr = Math.min(window.devicePixelRatio || 1, 2);

window.addEventListener("pointermove", (e) => {
  state.mouse.x = e.clientX / window.innerWidth - 0.5;
  state.mouse.y = e.clientY / window.innerHeight - 0.5;
});

// Build an atlas of every distinct non-space glyph, drawn once in the ink color.
function buildAtlas(model) {
  const chars = new Set();
  for (const row of model.chars) for (const ch of row) if (ch !== " ") chars.add(ch);

  const probe = document.createElement("canvas").getContext("2d");
  probe.font = `${FONT_PX * dpr}px "DejaVu Sans Mono", monospace`;
  const cw = Math.ceil(probe.measureText("M").width);
  const ch = Math.ceil(FONT_PX * dpr * 1.32); // cell height with a little leading

  const list = [...chars];
  const atlas = document.createElement("canvas");
  atlas.width = Math.max(1, cw * list.length);
  atlas.height = ch;
  const actx = atlas.getContext("2d");
  actx.font = `${FONT_PX * dpr}px "DejaVu Sans Mono", monospace`;
  actx.textBaseline = "top";
  actx.fillStyle = PALETTE.ink;

  const index = new Map();
  list.forEach((g, i) => {
    index.set(g, i * cw);
    actx.fillText(g, i * cw, 0);
  });
  return { canvas: atlas, w: cw, h: ch, index };
}

function layout() {
  const { model, atlas } = state;
  canvas.width = model.cols * atlas.w;
  canvas.height = model.rows * atlas.h;
  canvas.style.width = `${canvas.width / dpr}px`;
  canvas.style.height = `${canvas.height / dpr}px`;
}

function precomputeDelays() {
  const { model, mode } = state;
  const subject = model.subject; // flat 0/1 array, present only when segmentation ran
  const d = new Float32Array(model.rows * model.cols);
  for (let r = 0; r < model.rows; r++) {
    for (let c = 0; c < model.cols; c++) {
      const i = r * model.cols + c;
      const base = revealDelay(mode, r, c, model.rows, model.cols);
      // With a subject mask, the background reveals first and the figure emerges after.
      d[i] = subject ? phasedDelay(base, subject[i] === 1) : base;
    }
  }
  state.delays = d;
}

function frame(nowMs) {
  const { model, atlas, delays, depth } = state;
  const subject = model.subject;
  if (!state.start) state.start = nowMs;
  const t = (nowMs - state.start) / 1000;

  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Virtual camera for depth parallax: a slow auto orbit nudged by the pointer.
  const amp = 7 * dpr;
  const camX = (Math.sin(t * 0.5) * 0.6 + state.mouse.x) * amp;
  const camY = (Math.cos(t * 0.4) * 0.4 + state.mouse.y) * amp * 0.7;

  let settled = true;
  for (let r = 0; r < model.rows; r++) {
    const row = model.chars[r];
    for (let c = 0; c < model.cols; c++) {
      const ch = row[c];
      if (ch === " ") continue;
      const x0 = atlas.index.get(ch);
      if (x0 === undefined) continue;

      const i = r * model.cols + c;
      const p = cellProgress(t, delays[i], REVEAL.stagger, REVEAL.duration);
      if (p <= 0) {
        settled = false;
        continue;
      }
      if (p < 1) settled = false;

      // Reveal: fade in while sliding up the last few pixels. Cheap per-cell transform
      // that still reads as the grid assembling itself.
      ctx.globalAlpha = p;
      let dx = 0;
      let dy = (1 - p) * atlas.h * 0.4;

      // Once settled, add continuous motion. Depth parallax takes precedence: each cell
      // shifts by the camera offset scaled by its depth, so the scene gains real space.
      // Without depth, fall back to the segmentation drift (subject floats, background
      // holds). Either way the frame stops being a static block.
      if (p >= 1) {
        if (depth) {
          const [px, py] = parallaxOffset(depth[i], camX, camY);
          dx += px;
          dy += py;
        } else if (subject && subject[i] === 1) {
          dx += Math.sin(t * 1.1 + r * 0.22) * 1.6 * dpr;
          dy += Math.cos(t * 0.85 + c * 0.18) * 1.3 * dpr;
        }
      }

      ctx.drawImage(atlas.canvas, x0, 0, atlas.w, atlas.h, c * atlas.w + dx, r * atlas.h + dy, atlas.w, atlas.h);
    }
  }
  ctx.globalAlpha = 1;

  // Keep animating until every cell has arrived. Depth or subject motion continues
  // forever, so keep the loop alive; otherwise stop once the grid has settled.
  if (!settled || subject || depth) requestAnimationFrame(frame);
}

function play() {
  state.start = 0;
  requestAnimationFrame(frame);
}

function loadModel(model) {
  state.model = model;
  state.atlas = buildAtlas(model);
  // Depth arrives as a byte per cell; back to [0,1] for parallax.
  state.depth = model.depth ? Float32Array.from(model.depth, (d) => d / 255) : null;
  layout();
  precomputeDelays();
  play();
}

// Wire the controls: reveal-mode buttons and a replay.
document.querySelectorAll("[data-mode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    precomputeDelays();
    play();
  });
});
document.getElementById("replay").addEventListener("click", play);

// Load a frame model the engine produced (cli.py writes <name>.json).
document.getElementById("file").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (f) loadModel(JSON.parse(await f.text()));
});

// Boot with the bundled sample so the page shows something immediately.
fetch("sample.json")
  .then((r) => r.json())
  .then(loadModel)
  .catch(() => {
    document.getElementById("hint").textContent =
      "Load a frame .json produced by cli.py to begin.";
  });
