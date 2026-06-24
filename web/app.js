// Browser glue: load a frame model, build a glyph atlas, and animate the character
// grid on a canvas. The smoothness ideas live here:
//   - render each unique glyph once into an offscreen atlas, then blit sprites with
//     drawImage instead of calling fillText thousands of times per frame
//   - drive everything off requestAnimationFrame with a real clock, so the easing is
//     frame-rate independent and does not speed up on a faster display
//   - scale the canvas by devicePixelRatio so text stays crisp
import { revealDelay, cellProgress } from "./anim.js";

const PALETTE = { paper: "#f3efe6", ink: "#221f1c" }; // warm, ink-on-paper
const FONT_PX = 16;
const REVEAL = { stagger: 1.6, duration: 0.6 }; // seconds

const state = {
  model: null,
  atlas: null, // { canvas, w, h, index: Map<char, x> }
  delays: null, // Float32Array of normalized per-cell start offsets
  mode: "wipe",
  start: 0,
};

const canvas = document.getElementById("stage");
const ctx = canvas.getContext("2d");
const dpr = Math.min(window.devicePixelRatio || 1, 2);

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
  const d = new Float32Array(model.rows * model.cols);
  for (let r = 0; r < model.rows; r++) {
    for (let c = 0; c < model.cols; c++) {
      d[r * model.cols + c] = revealDelay(mode, r, c, model.rows, model.cols);
    }
  }
  state.delays = d;
}

function frame(nowMs) {
  const { model, atlas, delays } = state;
  if (!state.start) state.start = nowMs;
  const t = (nowMs - state.start) / 1000;

  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  let settled = true;
  for (let r = 0; r < model.rows; r++) {
    const row = model.chars[r];
    for (let c = 0; c < model.cols; c++) {
      const ch = row[c];
      if (ch === " ") continue;
      const x0 = atlas.index.get(ch);
      if (x0 === undefined) continue;

      const p = cellProgress(t, delays[r * model.cols + c], REVEAL.stagger, REVEAL.duration);
      if (p <= 0) {
        settled = false;
        continue;
      }
      if (p < 1) settled = false;

      // Reveal: fade in while sliding up the last few pixels. Cheap per-cell transform
      // that still reads as the grid assembling itself.
      ctx.globalAlpha = p;
      const dy = (1 - p) * atlas.h * 0.4;
      ctx.drawImage(atlas.canvas, x0, 0, atlas.w, atlas.h, c * atlas.w, r * atlas.h + dy, atlas.w, atlas.h);
    }
  }
  ctx.globalAlpha = 1;

  // Keep animating until every cell has arrived, then idle (one more cheap repaint
  // would just redraw the same thing, so stop scheduling).
  if (!settled) requestAnimationFrame(frame);
}

function play() {
  state.start = 0;
  requestAnimationFrame(frame);
}

function loadModel(model) {
  state.model = model;
  state.atlas = buildAtlas(model);
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
