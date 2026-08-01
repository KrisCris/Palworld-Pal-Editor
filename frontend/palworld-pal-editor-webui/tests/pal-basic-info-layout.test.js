import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const readSource = async relativePath => {
  try {
    return await readFile(new URL(relativePath, import.meta.url), "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return "";
    throw error;
  }
};

const [source, mainCss, editorCss, selectorSource] = await Promise.all([
  readSource("../src/components/PalEditor.vue"),
  readSource("../src/assets/main.css"),
  readSource("../src/assets/editor-ui.css"),
  readSource("../src/components/modules/PalSpeciesSelector.vue"),
]);

const basicPanel = () => {
  const start = source.indexOf('data-testid="pal-basic-info"');
  const end = source.indexOf('<div class="pal-progression-grid">');
  assert.notEqual(start, -1, "Pal basic info boundary");
  assert.notEqual(end, -1, "Pal basic info end");
  return source.slice(start, end);
};

test("the shared editor design foundation is globally loaded", () => {
  assert.match(mainCss, /@import ['"]\.\/editor-ui\.css['"]/);

  for (const token of [
    "--editor-color-background",
    "--editor-color-surface",
    "--editor-color-surface-raised",
    "--editor-color-control",
    "--editor-color-border",
    "--editor-color-focus",
    "--editor-color-success",
    "--editor-color-warning",
    "--editor-color-passive-top",
    "--editor-control-height",
  ]) {
    assert.equal(editorCss.includes(token), true, token);
  }

  for (const primitive of [
    ".editor-surface",
    ".editor-summary",
    ".editor-section",
    ".editor-field",
    ".editor-control",
    ".editor-button",
    ".editor-tag",
    ".editor-stepper",
    ".editor-stat-grid",
    ".editor-disclosure",
  ]) {
    assert.equal(editorCss.includes(primitive), true, primitive);
  }
});

test("Pal basic info is isolated from legacy visual classes", () => {
  const panel = basicPanel();
  for (const primitive of [
    "editor-surface",
    "editor-summary",
    "editor-section",
    "editor-field",
    "editor-control",
    "editor-button",
    "editor-tag",
    "editor-stepper",
    "editor-stat-grid",
    "editor-disclosure",
  ]) {
    assert.equal(panel.includes(primitive), true, primitive);
  }
  assert.doesNotMatch(panel, /(?:class|:class)="[^"]*\b(?:EditorItem|const|edit|selector)\b/);
  assert.doesNotMatch(source, /button#(?:dump|dupe|del)_btn\s*\{/);
  assert.match(source, /\.pal-editor\s*\{/);
});

test("Pal basic info composes by container size instead of viewport size", () => {
  assert.match(source, /\.pal-basic-info\s*\{[^}]*container-type:\s*inline-size/s);
  assert.match(source, /@container\s+pal-basic-info\s*\(max-width:\s*720px\)/);
  assert.match(source, /@container\s+pal-basic-info\s*\(max-width:\s*420px\)/);
  assert.match(source, /@container\s+pal-basic-info\s*\(max-width:\s*720px\)[\s\S]*?\.editor-summary__actions\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/);
  assert.match(editorCss, /\.editor-control\s*\{[^}]*min-width:\s*0[^}]*box-sizing:\s*border-box/s);
  assert.match(editorCss, /\.editor-field__actions\s*\{[^}]*flex-shrink:\s*0/s);
});

test("Pal summary uses Paldeck identity without duplicate or N/A tags", () => {
  const panel = basicPanel();
  assert.match(source, /import \{ paldeckForRow \}/);
  assert.match(source, /import PalPortrait from/);
  assert.match(panel, /<PalPortrait[^>]*size="5\.5rem"/s);
  assert.match(panel, /<template #top-left>[\s\S]*?v-if="palStore\.SELECTED_PAL_DATA\.IsBOSS"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/boss'\)"/);
  assert.match(panel, /<template #top-left>[\s\S]*?v-else-if="palStore\.SELECTED_PAL_DATA\.IsRarePal"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/rare'\)"/);
  assert.match(panel, /<template #top-right>[\s\S]*?v-if="palStore\.SELECTED_PAL_DATA\.IsBOSS && palStore\.SELECTED_PAL_DATA\.IsRarePal"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/rare'\)"/);
  assert.match(panel, /PAL \$\{currentPaldeck\(\)\}/);
  assert.doesNotMatch(panel.match(/<h2[\s\S]*?<\/h2>/)?.[0] || "", /displayPalElement/);
  assert.match(panel, /specialTypeKeys\(palStore\.SELECTED_PAL_DATA\)\.length/);
  assert.doesNotMatch(panel, /displaySpecialType|displayPalElement/);
});

test("Pal basic info keeps specific translated icon action names", () => {
  const panel = basicPanel();
  for (const key of [
    "Editor_Btn_Friendship_Decrease",
    "Editor_Btn_Friendship_Increase",
    "Editor_Btn_Friendship_Max",
    "Editor_Btn_Level_Decrease",
    "Editor_Btn_Level_Increase",
    "Editor_Btn_Level_Max",
    "Editor_Btn_Toggle_Boss",
    "Editor_Btn_Toggle_Rare",
  ]) {
    assert.match(panel, new RegExp(`:aria-label="palStore\\.getTranslatedText\\('${key}'\\)"`));
  }
});

test("the Pal species selector consumes shared editor tokens", () => {
  for (const selector of [
    ".selector-trigger",
    ".selector-popover",
    ".search-label input",
    ".selector-pane",
    ".selector-actions button",
  ]) {
    const escaped = selector.replaceAll(".", "\\.").replaceAll(" ", "\\s+");
    assert.match(selectorSource, new RegExp(`${escaped}\\s*\\{[^}]*var\\(--editor-`, "s"), selector);
  }
});
