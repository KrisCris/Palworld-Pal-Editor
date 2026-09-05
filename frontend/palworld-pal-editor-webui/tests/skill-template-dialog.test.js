import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { createPinia, setActivePinia } from "pinia";

import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

after(closeVueServer);

test("skill templates keep overflow hidden until its card is explicitly expanded", async () => {
  const [{ default: SkillTemplateDialog }, { useTemplatesStore }, { useCatalogsStore }] = await Promise.all([
    loadVueModule("/src/components/SkillTemplateDialog.vue"),
    loadVueModule("/src/stores/templates.js"),
    loadVueModule("/src/stores/catalogs.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const skills = Array.from({ length: 6 }, (_, index) => `Passive${index + 1}`);
  useTemplatesStore().skillTemplates = [{
    templateId: "worker", name: "Worker passives", type: "passive", PassiveSkillList: skills,
  }];
  useCatalogsStore().passiveSkills = skills.map((skill, index) => ({
    InternalName: skill,
    I18n: [`Passive ${index + 1}`, `Effect ${index + 1}`],
    Rating: index + 1,
  }));

  const html = await renderVue(SkillTemplateDialog, { pinia, props: { type: "passive" } });
  assert.match(html, /role="dialog"/);
  assert.match(html, /Worker passives/);
  assert.match(html, /template-skills--summary/);
  assert.match(html, /Passive 1/);
  assert.match(html, /Effect 1/);
  assert.match(html, /passive-tier--positive/);
  assert.doesNotMatch(html, /template-skills--overflow|Passive 5|Effect 6/);
  assert.match(html, /template-skills__toggle/);
  assert.match(html, /aria-expanded="false"/);
  assert.match(html, /Expand skills/);
  assert.match(html, /\+2/);
  assert.match(html, /Save current group/);
  assert.match(html, /Apply/);

  const source = await readFile(new URL("../src/components/SkillTemplateDialog.vue", import.meta.url), "utf8");
  assert.match(source, /function toggleExpanded\(template\)/);
  assert.match(source, /overflowSkills\(template\)\.length && isExpanded\(template\)/);
  assert.match(source, /@click="toggleExpanded\(template\)"/);
  assert.doesNotMatch(source, /template-card:hover \.template-skills--overflow|template-card:focus-within \.template-skills--overflow/);
});

test("active template cards only render equipped skills with compact combat metadata", async () => {
  const [{ default: SkillTemplateDialog }, { useTemplatesStore }, { useCatalogsStore }] = await Promise.all([
    loadVueModule("/src/components/SkillTemplateDialog.vue"),
    loadVueModule("/src/stores/templates.js"),
    loadVueModule("/src/stores/catalogs.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  useTemplatesStore().skillTemplates = [{
    templateId: "combat", name: "Combat", type: "active",
    EquipWaza: ["EPalWazaID::AirCanon"],
    MasteredWaza: ["EPalWazaID::PowerShot"],
  }];
  useCatalogsStore().activeSkills = [
    { InternalName: "EPalWazaID::AirCanon", I18n: ["Air Cannon", "Air"], Element: "Neutral", Power: 25, CT: 2 },
    { InternalName: "EPalWazaID::PowerShot", I18n: ["Power Shot", "Power"], Element: "Neutral", Power: 35, CT: 4 },
  ];

  const html = await renderVue(SkillTemplateDialog, { pinia, props: { type: "active" } });
  assert.match(html, /Air Cannon/);
  assert.match(html, /Attack: 25/);
  assert.match(html, /CT: 2/);
  assert.doesNotMatch(html, /Power Shot|Equipped/);
});

test("Pal editor opens templates from both skill group headers", async () => {
  const source = await readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8");
  assert.match(source, /<SkillTemplateDialog/);
  assert.match(source, /openSkillTemplates\('passive'\)/);
  assert.match(source, /openSkillTemplates\('active'\)/);
});

test("skill template store supports create, rename, apply, delete, and reset", async () => {
  const source = await readFile(new URL("../src/stores/templates.js", import.meta.url), "utf8");
  for (const method of [
    "loadSkillTemplates",
    "saveSkillTemplate",
    "renameTemplate",
    "removeSkillTemplate",
  ]) assert.match(source, new RegExp(`function ${method}\\(`));

  const pals = await readFile(new URL("../src/stores/pals.js", import.meta.url), "utf8");
  // Applying one changes a Pal, so it goes through the Pal write path and
  // answers with the Pal; nothing re-reads it afterwards.
  assert.match(pals, /applySkillTemplate\(recordKey, templateId\)/);

  const editor = await readFile(new URL("../src/stores/paleditor.js", import.meta.url), "utf8");
  assert.ok(editor.match(/templates\.clear\(\)/g)?.length >= 2);
});
