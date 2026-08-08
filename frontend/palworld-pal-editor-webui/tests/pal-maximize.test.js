import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import en from "../src/i18n/en.js";
import zhCN from "../src/i18n/zh-CN.js";

const [editorSource, storeSource] = await Promise.all([
  readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8"),
  readFile(new URL("../src/stores/paleditor.js", import.meta.url), "utf8"),
]);

test("Pal summary exposes one legal attribute maximization action", () => {
  assert.match(editorSource, /id="maximize_pal_btn"/);
  assert.match(editorSource, /@click="palStore\.maximizePal"/);
  assert.match(editorSource, /<UiIcon name="maximum"/);
  assert.match(editorSource, /Editor_Btn_Maximize_Pal/);
});

test("Pal summary uses formal attribute and profile terminology", () => {
  assert.equal(en.Editor_Btn_Maximize_Pal, "Maximize attributes");
  assert.equal(zhCN.Editor_Btn_Maximize_Pal, "属性最大化");
  assert.equal(en.Editor_Identity_Appearance, "PROFILE & APPEARANCE");
  assert.equal(zhCN.Editor_Identity_Appearance, "档案与外观");
});

test("maximize action atomically refreshes and marks the selected Pal", () => {
  assert.match(storeSource, /async function maximizePal\(\)/);
  assert.match(storeSource, /POST\("\/api\/pal\/maximize"/);
  assert.match(storeSource, /new PalData\(\{[\s\S]*\.\.\.response\.data[\s\S]*\}\)/);
  assert.match(storeSource, /EDITED_PAL_IDS\.value\.add\(SELECTED_PAL_ID\.value\)/);
  assert.match(storeSource, /Message_Pal_Maximized/);
  assert.match(storeSource, /Operation_Maximize_Pal/);
  assert.match(storeSource, /\n\s*maximizePal,/);
});
