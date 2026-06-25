// Pure animation math, kept free of the DOM so it can be unit tested in Node.
// The browser glue in app.js imports these.

export function clamp01(x) {
  return x < 0 ? 0 : x > 1 ? 1 : x;
}

// easeOutCubic: fast start, gentle settle. The house easing for the reveal so cells
// arrive smoothly instead of snapping.
export function easeOutCubic(t) {
  const u = 1 - clamp01(t);
  return 1 - u * u * u;
}

// A small deterministic hash of a cell's coordinates to a value in [0,1). Used by the
// scatter reveal so each cell gets a stable pseudo-random delay without storing one.
export function hash01(r, c) {
  let h = (r * 73856093) ^ (c * 19349663);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h >>> 0) % 100000) / 100000;
}

// revealDelay returns a normalized start offset in [0,1) for a cell, by mode. The
// animator multiplies it by the total stagger window to get a real start time.
export function revealDelay(mode, r, c, rows, cols) {
  switch (mode) {
    case "rows":
      return rows > 1 ? r / (rows - 1) : 0;
    case "radial": {
      const cr = (rows - 1) / 2;
      const cc = (cols - 1) / 2;
      const d = Math.hypot(r - cr, c - cc);
      const max = Math.hypot(cr, cc) || 1;
      return d / max;
    }
    case "scatter":
      return hash01(r, c);
    case "wipe":
    default:
      // Diagonal sweep from the top-left corner.
      return (r + c) / (rows + cols - 2 || 1);
  }
}

// phasedDelay splits the reveal when a subject mask is present: the background fills
// first, then the subject emerges on top. Background maps into [0, 0.55), the subject
// into [0.5, 1], so they overlap slightly and the figure appears to rise out of the
// scene rather than arriving at the same time.
export function phasedDelay(baseDelay, isSubject) {
  const BG_END = 0.55;
  const SUBJECT_START = 0.5;
  return isSubject ? SUBJECT_START + baseDelay * (1 - SUBJECT_START) : baseDelay * BG_END;
}

// parallaxOffset shifts a cell by the camera offset scaled by its depth (1 = nearest),
// so near characters move more than far ones as the camera pans and a flat image gains
// a sense of space.
export function parallaxOffset(depth, camX, camY) {
  return [camX * depth, camY * depth];
}

// cellProgress maps wall-clock time to a cell's 0..1 reveal progress, eased. now and
// the windows are in seconds. stagger is how long the start times are spread over;
// duration is how long one cell takes to arrive.
export function cellProgress(now, normalizedDelay, stagger, duration) {
  const start = normalizedDelay * stagger;
  return easeOutCubic((now - start) / duration);
}
