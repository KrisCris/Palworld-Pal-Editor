import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8");

test("Pal progression and skill editors use the compact shared layout", () => {
  for (const className of [
    "pal-editor", "pal-progression-grid", "pal-panel", "range-grid",
    "suitability-grid", "skill-section", "skill-cards",
  ]) assert.match(source, new RegExp(`class="[^"]*${className}`), className);

  assert.match(source, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(14rem,\s*1fr\)\)/);
  assert.match(source, /@container\s+pal-editor\s*\(max-width:\s*42rem\)/);
  assert.doesNotMatch(source, /EditorItem|editField|skillPanel|flex-v|@mouseup|@touchend|--sub-height|--editor-panel-width/);
});

test("range controls preserve limits and update from keyboard-friendly change events", () => {
  for (const field of [
    "Talent_HP", "Talent_Defense", "Talent_Shot", "Talent_Melee",
    "Rank_HP", "Rank_Attack", "Rank_Defence", "Rank_CraftSpeed", "Rank",
  ]) {
    assert.match(source, new RegExp(`name="${field}"[\\s\\S]*?@change="palStore\\.updatePal"`), field);
  }
  assert.match(source, /palStore\.HIDE_INVALID_OPTIONS \? 100 : 255/);
  assert.match(source, /palStore\.HIDE_INVALID_OPTIONS \? palStore\.MAX_SOULS_LEVEL : 255/);
  assert.match(source, /palStore\.HIDE_INVALID_OPTIONS \? 5 : 255/);
});

test("all Pal edit contracts and validity rules remain available", () => {
  for (const handler of [
    "toggleAwakening", "suitDown", "suitUp", "pop_PassiveSkillList",
    "add_PassiveSkillList", "pop_EquipWaza", "add_EquipWaza",
    "pop_MasteredWaza", "add_MasteredWaza",
  ]) assert.match(source, new RegExp(handler), handler);

  assert.match(source, /key != 'EPalWorkSuitability::OilExtraction'/);
  assert.match(source, /Assignable === false/);
  assert.match(source, /elementIconKey/);
  assert.match(source, /skillBadgeLabels/);
  assert.match(source, /canToggleBossVariant/);
});
