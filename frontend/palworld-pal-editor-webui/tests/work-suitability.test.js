import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { maximumSuitabilities } from "../src/stores/paleditor.js";

test("maximum suitability payload includes only work types available to this Pal", () => {
  assert.deepEqual(
    maximumSuitabilities({ Handcraft: 2, Mining: 1, OilExtraction: 0 }, 5),
    { Handcraft: 5, Mining: 5 },
  );
});

test("work suitability panel exposes one max-all action", async () => {
  const source = await readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8");
  assert.match(source, /@click="palStore\.SELECTED_PAL_DATA\.maxSuitabilities"/);
  assert.match(source, /Editor_Suitabilities_Max/);
});
