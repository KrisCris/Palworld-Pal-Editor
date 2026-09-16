import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";

// A full-viewport overlay: fixed to the viewport and covering it.
const OVERLAY = /position:\s*fixed[^}]*inset:\s*0|inset:\s*0[^}]*position:\s*fixed/s;

const componentDir = new URL("../src/components/", import.meta.url);
const names = (await readdir(componentDir)).filter(name => name.endsWith(".vue"));
const sources = Object.fromEntries(await Promise.all(
  names.map(async name => [name, await readFile(new URL(name, componentDir), "utf8")]),
));
const app = await readFile(new URL("../src/App.vue", import.meta.url), "utf8");
const editorView = await readFile(new URL("../src/views/EditorView.vue", import.meta.url), "utf8");

test("an overlay opened from inside the editor canvas teleports out of it", async () => {
  // `.editor-canvas` sets `isolation: isolate`, so it is a stacking context: a
  // backdrop rendered inside it cannot rise above the roster rails, which are the
  // canvas's *siblings* with their own z-index. No z-index on the backdrop can fix
  // that from within -- the item picker carried `z-index: 1000` and still opened
  // underneath both rails, with its left ~380px covered and unclickable.
  //
  // The overlays App.vue mounts itself are exempt: they are already above the
  // canvas rather than inside it.
  assert.match(editorView, /isolation:\s*isolate/);

  const trapped = names.filter(name => OVERLAY.test(sources[name])
    && !app.includes(`components/${name}`));
  assert.ok(trapped.length, "no canvas-mounted overlays found to check");
  for (const name of trapped) {
    assert.match(sources[name], /<Teleport to="body">/, name);
  }
});

test("the overlays App.vue mounts are the only ones exempt", () => {
  // Named so that moving one of these down into the canvas trips the test above
  // instead of silently reintroducing the bug.
  const exempt = names.filter(name => OVERLAY.test(sources[name])
    && app.includes(`components/${name}`));
  assert.deepEqual(exempt.sort(), ["MessageCenter.vue", "SupportDialog.vue"]);
});
