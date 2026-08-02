import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { closeVueServer, loadVueModule } from "./vue-render.js";

after(closeVueServer);

test("segmented ranges normalize item, stat, and empty track spans", async () => {
  const { normalizeRangeSegments } = await loadVueModule("/src/components/modules/SegmentedRange.vue");

  assert.deepEqual(normalizeRangeSegments({
    min: 0,
    max: 50,
    value: 45,
    segments: [
      { role: "item", value: 30 },
      { role: "primary", value: 15 },
    ],
  }), [
    { role: "item", start: 0, end: 60 },
    { role: "primary", start: 60, end: 90 },
    { role: "empty", start: 90, end: 100 },
  ]);

  assert.deepEqual(normalizeRangeSegments({ min: 0, max: 5, value: 3 }), [
    { role: "primary", start: 0, end: 60 },
    { role: "empty", start: 60, end: 100 },
  ]);
});

test("Pal progression controls use the shared range component", async () => {
  const source = await readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8");
  assert.match(source, /import SegmentedRange/);
  assert.equal((source.match(/<SegmentedRange/g) || []).length, 9);
  assert.doesNotMatch(source, /<input type="range"/);
  assert.match(source, /const updateRange = \(name, value\)/);
});
