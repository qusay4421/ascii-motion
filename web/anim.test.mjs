import { test } from "node:test";
import assert from "node:assert/strict";
import { clamp01, easeOutCubic, hash01, revealDelay, cellProgress } from "./anim.js";

test("clamp01 bounds to [0,1]", () => {
  assert.equal(clamp01(-2), 0);
  assert.equal(clamp01(0.5), 0.5);
  assert.equal(clamp01(9), 1);
});

test("easeOutCubic hits the endpoints and eases out", () => {
  assert.equal(easeOutCubic(0), 0);
  assert.equal(easeOutCubic(1), 1);
  assert.ok(easeOutCubic(0.5) > 0.5, "ease-out is ahead of linear at the midpoint");
});

test("hash01 is deterministic and in range", () => {
  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 5; c++) {
      const v = hash01(r, c);
      assert.ok(v >= 0 && v < 1);
      assert.equal(v, hash01(r, c)); // stable
    }
  }
});

test("wipe reveal sweeps from the top-left corner to the bottom-right", () => {
  assert.equal(revealDelay("wipe", 0, 0, 10, 10), 0);
  assert.equal(revealDelay("wipe", 9, 9, 10, 10), 1);
  assert.ok(revealDelay("wipe", 0, 5, 10, 10) < revealDelay("wipe", 9, 5, 10, 10));
});

test("radial reveal starts at the center and grows outward", () => {
  const center = revealDelay("radial", 5, 5, 11, 11);
  const corner = revealDelay("radial", 0, 0, 11, 11);
  assert.ok(center < 0.05);
  assert.ok(Math.abs(corner - 1) < 1e-9);
});

test("rows reveal is proportional to the row index", () => {
  assert.equal(revealDelay("rows", 0, 3, 11, 5), 0);
  assert.equal(revealDelay("rows", 5, 3, 11, 5), 0.5);
  assert.equal(revealDelay("rows", 10, 3, 11, 5), 1);
});

test("scatter delays stay within range for every cell", () => {
  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 20; c++) {
      const d = revealDelay("scatter", r, c, 20, 20);
      assert.ok(d >= 0 && d < 1);
    }
  }
});

test("cellProgress is 0 before its start and 1 well after", () => {
  // delay 0.5 over a 2s stagger means this cell starts at t=1s.
  assert.equal(cellProgress(0.4, 0.5, 2, 0.6), 0);
  assert.equal(cellProgress(5, 0.5, 2, 0.6), 1);
  const mid = cellProgress(1.3, 0.5, 2, 0.6); // 0.3s into a 0.6s reveal
  assert.ok(mid > 0 && mid < 1);
});
