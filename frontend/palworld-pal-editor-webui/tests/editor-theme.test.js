import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const paths = {
  base: "../src/assets/base.css",
  editor: "../src/assets/editor-ui.css",
  workspace: "../src/views/EditorView.vue",
  topBar: "../src/components/TopBar.vue",
  players: "../src/components/PlayerList.vue",
  pals: "../src/components/PalList.vue",
  palEditor: "../src/components/PalEditor.vue",
  playerEditor: "../src/components/PlayerEditor.vue",
  species: "../src/components/modules/PalSpeciesSelector.vue",
  search: "../src/components/modules/SearchSelect.vue",
  technology: "../src/components/modules/TechCard.vue",
  messages: "../src/components/MessageCenter.vue",
  support: "../src/components/SupportDialog.vue",
  addPal: "../src/components/AddPalDialog.vue",
  pathPicker: "../src/components/PathPicker.vue",
  speciesSelector: "../src/components/modules/PalSpeciesSelector.vue",
  backendSelector: "../src/components/BackendServerSelector.vue",
  backendError: "../src/views/BackendErrorView.vue",
};

const sources = Object.fromEntries(await Promise.all(
  Object.entries(paths).map(async ([name, path]) => [
    name,
    await readFile(new URL(path, import.meta.url), "utf8"),
  ]),
));
const editorSources = Object.values(sources).join("\n");
const tokenHex = token => sources.editor.match(new RegExp(`${token}:\\s*(#[0-9a-f]{6})`, "i"))?.[1];
const rgb = hex => hex.match(/[0-9a-f]{2}/gi).map(channel => Number.parseInt(channel, 16));
const mix = (foreground, amount, background) => rgb(foreground)
  .map((channel, index) => Math.round(channel * amount + rgb(background)[index] * (1 - amount)));
const luminance = color => color.map(channel => {
  const value = channel / 255;
  return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
}).reduce((total, channel, index) => total + channel * [.2126, .7152, .0722][index], 0);
const contrast = (left, right) => {
  const [lighter, darker] = [luminance(left), luminance(right)].sort((a, b) => b - a);
  return (lighter + .05) / (darker + .05);
};

test("the loaded editor defines and consumes one semantic color system", () => {
  for (const [token, value] of Object.entries({
    "--editor-color-background": "#0a0c0d",
    "--editor-color-surface": "#181c1f",
    "--editor-color-surface-raised": "#2c3135",
    "--editor-color-border": "#596873",
    "--editor-color-primary": "#20b7ff",
    "--editor-color-primary-hover": "#55c8ff",
    "--editor-color-backdrop-warm": "#ff4563",
    "--editor-color-focus": "#20b7ff",
    "--editor-color-ancient": "#9a4dff",
    "--editor-color-lucky": "#54c7ff",
  })) assert.match(sources.editor, new RegExp(`${token}:\\s*${value}`, "i"));

  for (const [name, source] of Object.entries(sources)) {
    assert.match(source, /var\(--editor-color-/, name);
  }

  assert.match(sources.base, /--color-background:\s*var\(--editor-color-background\)/);
  assert.match(sources.base, /--color-text:\s*var\(--editor-color-text\)/);
});

test("editor states share vivid semantic accents", () => {
  assert.match(sources.players, /\[aria-current=["']true["']\]\s*\{[^}]*border-color:\s*var\(--editor-color-focus\)[^}]*background:\s*var\(--editor-color-surface-raised\)/s);
  assert.match(sources.pals, /\[aria-current=["']true["']\]\s*\{[^}]*border-color:\s*var\(--pal-row-accent\)[^}]*background:\s*var\(--editor-color-surface-raised\)/s);
  for (const source of [sources.players, sources.pals]) {
    assert.doesNotMatch(source, /\[aria-current=["']true["']\]\s*\{[^}]*linear-gradient/s);
  }

  assert.match(sources.topBar, /\.op\.toggled\s*\{[^}]*var\(--editor-color-success\)/s);
  assert.match(sources.pals, /var\(--editor-color-male\)/);
  assert.match(sources.pals, /var\(--editor-color-female\)/);
  assert.match(sources.pals, /var\(--editor-color-success\)/);
  for (const source of [sources.pals, sources.palEditor]) {
    assert.match(source, /pal\.IsBOSS\s*\?\s*['"]var\(--editor-color-danger\)['"]\s*:\s*pal\.IsRarePal\s*\?\s*['"]var\(--editor-color-lucky\)['"]/s);
    assert.doesNotMatch(source, /var\(--editor-color-ancient\)/);
  }

  assert.match(sources.species, /\.warning\s*\{[^}]*var\(--editor-color-warning\)/s);
  for (const source of [sources.palEditor, sources.search]) {
    for (const tier of ["top", "high", "positive", "negative"])
      assert.match(source, new RegExp(`var\\(--editor-color-passive-${tier}\\)`));
  }
});

test("workspace uses the selected Palworld color lighting and glass surfaces", () => {
  assert.match(sources.base, /body\s*\{[^}]*background:\s*var\(--color-background\);[^}]*background:\s*radial-gradient/s);
  assert.match(sources.base, /radial-gradient\([^}]*var\(--editor-color-backdrop-warm\)[^}]*radial-gradient\([^}]*var\(--editor-color-focus\)[^}]*radial-gradient\([^}]*var\(--editor-color-ancient\)/s);
  assert.match(sources.editor, /--editor-glass-filter:\s*blur\(26px\) saturate\(125%\)/);
  assert.match(sources.editor, /\.editor-surface\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)[^}]*\n\s*backdrop-filter:\s*var\(--editor-glass-filter\)[^}]*box-shadow:\s*var\(--editor-glass-shadow\)/s);
  assert.match(sources.workspace, /\.editor-roster\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)/s);
  assert.doesNotMatch(sources.workspace, /\.editor-roster\s*\{[^}]*backdrop-filter:/s);
  assert.match(sources.workspace, /\.editor-roster::before\s*\{[^}]*inset:\s*0;[^}]*backdrop-filter:\s*var\(--editor-glass-filter\)/s);
  assert.doesNotMatch(sources.topBar, /\.editor-toolbar\s*\{[^}]*backdrop-filter:/s);
  assert.match(sources.topBar, /\.editor-toolbar::before\s*\{[^}]*background:\s*var\(--editor-color-glass-toolbar\)[^}]*backdrop-filter:\s*var\(--editor-glass-filter\)/s);
  assert.match(sources.topBar, /\.editor-roster-preview\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)[^}]*backdrop-filter:\s*var\(--editor-glass-filter\)/s);
  assert.match(sources.playerEditor, /\.player-summary,[\s\S]*?\.player-panel\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)[^}]*backdrop-filter:\s*var\(--editor-glass-filter\)/s);

  assert.ok(contrast(
    rgb(tokenHex("--editor-color-border")),
    rgb(tokenHex("--editor-color-control")),
  ) >= 3, "control boundary");
});

test("floating dialogs share the restrained glass surface and overlay", () => {
  assert.match(sources.editor, /\.editor-glass-surface\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)[^}]*backdrop-filter:\s*var\(--editor-glass-filter\)[^}]*box-shadow:\s*var\(--editor-glass-shadow\)/s);
  assert.match(sources.editor, /\.editor-modal-overlay::before\s*\{[^}]*background:\s*color-mix\([^}]*var\(--editor-color-background\)[^}]*backdrop-filter:\s*blur\(/s);

  for (const source of [sources.messages, sources.support, sources.addPal, sources.pathPicker, sources.speciesSelector, sources.backendSelector])
    assert.match(source, /editor-glass-surface/);
  for (const source of [sources.messages, sources.support, sources.addPal, sources.pathPicker, sources.speciesSelector])
    assert.match(source, /editor-modal-overlay/);
  assert.match(sources.backendError, /editor-glass-surface/);
});

test("floating editor menus use the shared restrained glass surface", () => {
  assert.match(sources.search, /class="search-select__popover editor-glass-surface"/);
  assert.match(sources.pals, /class="pal-list-menu__popover editor-glass-surface"/);
  assert.match(sources.topBar, /class="editor-more__menu editor-glass-surface"/);
  for (const [source, selector] of [
    [sources.search, "search-select__popover"],
    [sources.pals, "pal-list-menu__popover"],
    [sources.topBar, "editor-more__menu"],
  ]) {
    assert.doesNotMatch(source, new RegExp(`\\.${selector}\\s*\\{[^}]*background:\\s*var\\(--editor-color-surface-raised\\)`, "s"));
  }
});

test("rendered technology cards consume the shared palette", () => {
  assert.doesNotMatch(sources.technology, /#[0-9a-f]{3,8}|rgba?\(/i);
  assert.match(sources.technology, /\.tech\s*\{[^}]*color:\s*var\(--editor-color-text\)[^}]*background-color:\s*var\(--editor-color-control\)/s);
  assert.match(sources.technology, /\.tech--boss\s*\{[^}]*var\(--editor-color-ancient\)/s);
  assert.match(sources.technology, /\.tech-header,[\s\S]*?\.tech-state\s*\{[^}]*background:\s*color-mix\([^}]*var\(--editor-color-background\)/s);
});

test("messages and support dialog use shared status and dialog colors", () => {
  assert.match(sources.messages, /\['message-toast', 'editor-glass-surface', current\.severity\]/);
  assert.doesNotMatch(sources.messages, /\.message-toast\s*\{[^}]*background:\s*var\(--editor-color-surface-raised\)/s);
  assert.match(sources.messages, /\.message-toast\.warning\s*\{[^}]*var\(--editor-color-warning\)/s);
  assert.match(sources.messages, /\.message-toast\.success\s*\{[^}]*var\(--editor-color-success\)/s);
  assert.match(sources.messages, /\.message-toast\.error\s*\{[^}]*var\(--editor-color-danger\)/s);
  assert.match(sources.messages, /\.message-dialog\.warning\s*\{[^}]*var\(--editor-color-warning\)/s);
  assert.match(sources.messages, /\.message-dialog\.success\s*\{[^}]*var\(--editor-color-success\)/s);
  assert.match(sources.messages, /\.message-dialog\.error\s*\{[^}]*var\(--editor-color-danger\)/s);

  for (const token of ["text", "primary", "danger"])
    assert.match(sources.support, new RegExp(`var\\(--editor-color-${token}\\)`));
});

test("saturated controls keep readable semantic foregrounds", () => {
  assert.match(sources.editor, /\.editor-button--primary\s*\{[^}]*color:\s*var\(--editor-color-background\)/s);
  assert.match(sources.topBar, /\.op--primary\s*\{[^}]*color:\s*var\(--editor-color-background\)[^}]*background:\s*var\(--editor-color-primary\)/s);
  assert.match(sources.species, /\.selector-actions \.apply:disabled\s*\{[^}]*var\(--editor-color-surface-subtle\)/s);
  assert.match(sources.support, /\.support-primary\s*\{[^}]*color:\s*var\(--editor-color-background\)[^}]*background:\s*var\(--editor-color-primary\)/s);
});

test("danger text controls meet normal-text contrast in normal and hover states", () => {
  assert.match(sources.editor, /\.editor-button--danger\s*\{[^}]*color:\s*var\(--editor-color-text\)[^}]*var\(--editor-color-danger\) 18%/s);
  assert.match(sources.editor, /\.editor-button--danger:hover\s*\{[^}]*color:\s*var\(--editor-color-text\)[^}]*var\(--editor-color-danger\) 30%/s);
  assert.doesNotMatch(sources.topBar, /\.op\.save|class="op save"/);

  const text = rgb(tokenHex("--editor-color-text"));
  const danger = tokenHex("--editor-color-danger");
  const raised = tokenHex("--editor-color-surface-raised");
  for (const amount of [.18, .30])
    assert.ok(contrast(text, mix(danger, amount, raised)) >= 4.5, `${amount * 100}% danger mix`);
});

test("selected selector descendants remain readable and warnings stay distinct", () => {
  assert.match(sources.species, /\.selector-pane button:hover small,[\s\S]*?\.selector-pane button\.selected small\s*\{[^}]*color:\s*var\(--editor-color-background\)/s);
  assert.match(sources.species, /\.selector-pane button:hover \.warning,[\s\S]*?\.selector-pane button\.selected \.warning\s*\{[^}]*color:\s*var\(--editor-color-warning\)[^}]*background:\s*var\(--editor-color-background\)/s);
  assert.match(sources.search, /\.search-select__options button:hover \.search-select__copy small,[\s\S]*?button\[aria-selected='true'\] \.search-select__copy small\s*\{[^}]*color:\s*var\(--editor-color-background\)/s);

  const dark = rgb(tokenHex("--editor-color-background"));
  const primary = rgb(tokenHex("--editor-color-primary"));
  const warning = rgb(tokenHex("--editor-color-warning"));
  assert.ok(contrast(dark, primary) >= 4.5, "selected description");
  assert.ok(contrast(warning, dark) >= 4.5, "selected warning badge");
});

test("loading-disabled controls stay neutral across component-specific states", () => {
  assert.match(sources.pals, /\.roster-icon-button:disabled\s*\{[^}]*border-color:\s*var\(--editor-color-disabled\)[^}]*color:\s*var\(--editor-color-muted\)[^}]*background:\s*var\(--editor-color-surface-subtle\)/s);
  assert.match(sources.topBar, /\.op:disabled,\s*\.op:disabled:hover,[\s\S]*?\{[^}]*background:\s*var\(--editor-color-surface-subtle\)/s);
  assert.ok(sources.topBar.indexOf(".op:disabled:hover") > sources.topBar.indexOf(".op--primary:hover"));
  assert.match(sources.technology, /\.tech:disabled\s*\{[^}]*border-color:\s*var\(--editor-color-disabled\)[^}]*color:\s*var\(--editor-color-muted\)[^}]*background-color:\s*var\(--editor-color-surface-subtle\)[^}]*filter:\s*grayscale\(1\)/s);
});

test("toolbar distinguishes primary commands from off and on toggles", () => {
  assert.match(sources.topBar, /class="op op--primary"[^>]*@click="save"/s);
  assert.match(sources.topBar, /class="op op--primary"[^>]*@click="palStore\.updatePal"/s);
  assert.doesNotMatch(sources.topBar, /\.editor-context-bar \.op\s*\{[^}]*var\(--editor-color-primary\)/s);
  assert.match(sources.topBar, /\.op,\s*#languageSelect,\s*\.savePath\s*\{[^}]*background:\s*var\(--editor-color-control\)/s);
  assert.match(sources.topBar, /\.op:hover\s*\{[^}]*border-color:\s*var\(--editor-color-primary\)[^}]*background:\s*var\(--editor-color-surface-raised\)/s);
  assert.match(sources.topBar, /\.op\.toggled\s*\{[^}]*border-color:\s*var\(--editor-color-success\)[^}]*color:\s*var\(--editor-color-success\)/s);
  assert.match(sources.topBar, /:aria-pressed="palStore\.SHOW_OOB_PAL_FLAG"/);
  assert.match(sources.topBar, /:aria-pressed="!palStore\.HIDE_INVALID_OPTIONS"/);
});

test("loaded-editor files contain no stale local palette values", () => {
  for (const stale of ["#3568b8", "#4077cf", "#3b2c18", "#183b29", "#3365da", "#35c982"])
    assert.equal(editorSources.includes(stale), false, stale);
});
