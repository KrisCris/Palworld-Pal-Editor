import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { createPinia, setActivePinia } from "pinia";

import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import ja from "../src/i18n/ja.js";
import zhCN from "../src/i18n/zh-CN.js";
import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

after(closeVueServer);

test("Add Pal dialog exposes default, template, and JSON workflows", async () => {
  const [
    { default: AddPalDialog }, { usePalEditorStore }, { useTemplatesStore },
  ] = await Promise.all([
    loadVueModule("/src/components/AddPalDialog.vue"),
    loadVueModule("/src/stores/paleditor.js"),
    loadVueModule("/src/stores/templates.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  const templates = useTemplatesStore();
  templates.palTemplates = [{
    templateId: "worker",
    name: "Worker",
    DisplayName: "Lamball",
    CharacterID: "SheepBall",
    IconAccessKey: "SheepBall",
    Level: 20,
    PassiveSkillList: ["CraftSpeed_up1"],
  }];

  const html = await renderVue(AddPalDialog, { pinia });
  assert.match(html, /role="dialog"/);
  for (const tab of ["Default Pal", "Templates", "Import JSON"]) {
    assert.match(html, new RegExp(`>${tab}<`));
  }
  assert.match(html, /Create Pal/);
});

test("the add dialog reads templates from the templates store", async () => {
  const source = await readFile(new URL("../src/components/AddPalDialog.vue", import.meta.url), "utf8");
  // The dialog names a template by the id the API gives it, so the create call
  // can pass it straight back as a `template` source.
  assert.match(source, /templatesStore\.palTemplates/);
  assert.match(source, /template\.templateId/);
  assert.doesNotMatch(source, /PAL_TEMPLATES/);
});

test("Add Pal dialog uses translated labels in every locale", () => {
  for (const locale of [en, fr, ja, zhCN]) {
    for (const key of [
      "AddPal_Title",
      "AddPal_Tab_Default",
      "AddPal_Tab_Templates",
      "AddPal_Tab_Json",
      "AddPal_Create",
      "AddPal_Save_Template",
    ]) assert.ok(locale[key], `${key} exists`);
  }
});

test("Pal list opens the dialog instead of creating immediately", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /<AddPalDialog/);
  assert.match(source, /@click="showAddPalDialog = true"/);
  assert.doesNotMatch(source, /@click="showAddPalDialog\.value = true"/);
  assert.doesNotMatch(source, /@click="palStore\.addPal"/);
});

test("Add Pal dialog traps focus and reuses the Pal brief for template previews", async () => {
  const source = await readFile(new URL("../src/components/AddPalDialog.vue", import.meta.url), "utf8");
  assert.match(source, /onBeforeUnmount/);
  assert.match(source, /setAttribute\('aria-hidden', 'true'\)/);
  assert.match(source, /function trapFocus/);
  assert.match(source, /dialog\.value\?\.focus/);
  assert.match(source, /PalBriefPanel/);
  assert.match(source, /templateBrief/);
  for (const field of ["Talent_HP", "Talent_Shot", "Talent_Defense", "MasteredWaza", "Suitabilities"]) {
    assert.match(source, new RegExp(field));
  }
  assert.doesNotMatch(source, /template-details/);
});

test("Pal templates are cleared when the editor resets or switches backends", async () => {
  const source = await readFile(new URL("../src/stores/paleditor.js", import.meta.url), "utf8");
  assert.ok(source.match(/templates\.clear\(\)/g)?.length >= 2);
});

test("Add Pal offers the storages the save says a new Pal may go in", async () => {
  const source = await readFile(new URL("../src/components/AddPalDialog.vue", import.meta.url), "utf8");
  // Which storages qualify is asked of the roster, not filtered out of the
  // directory by kind -- a viewing cage or another guild's base would otherwise
  // put the new Pal in a list nobody can open.
  assert.match(source, /loadCreationTargets\(\)/);
  assert.doesNotMatch(source, /ContainerKind|StorageKind/);
  assert.match(source, /v-model="targetStorageKey"/);
  assert.match(source, /storage\.occupied >= storage\.capacity/);
  assert.match(source, /targetStorageKey: targetStorageKey\.value/);
  assert.match(source, /formatStorageLabel/);
});
