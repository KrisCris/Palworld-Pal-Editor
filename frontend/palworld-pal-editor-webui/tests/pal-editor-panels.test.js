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
  assert.match(source, /\/image\/ui\/soul/);
});

test("range controls preserve limits and update from keyboard-friendly change events", () => {
  for (const field of [
    "Talent_HP", "Talent_Defense", "Talent_Shot", "Talent_Melee",
    "Rank_HP", "Rank_Attack", "Rank_Defence", "Rank_CraftSpeed", "Rank",
  ]) {
    assert.match(source, new RegExp(`name="${field}"[\\s\\S]*?@change="updateRange\\('${field}', \\$event\\)"`), field);
  }
  assert.doesNotMatch(source, /<input type="range"/);
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
  assert.match(source, /canAssignActiveSkill/);
  assert.match(source, /elementIconKey/);
  assert.match(source, /activeSkillMetadata/);
  assert.match(source, /canToggleBossVariant/);
});

test("skill card rows stay compact and do not add a redundant warning row", () => {
  assert.match(source, /\.skill-card__identity strong,[\s\S]*?white-space:\s*nowrap;/);
  assert.doesNotMatch(source, /class="skill-warning"/);
});

test("non-Pal passive skills stay cheat-only without a duplicate UI warning", () => {
  assert.match(source, /PASSIVE_SKILLS_LIST\s*\.filter\(skill => !palStore\.HIDE_INVALID_OPTIONS \|\| !skill\.Invalid\)/);
  assert.doesNotMatch(source, /<UiIcon v-if="palStore\.PASSIVE_SKILLS\[skill\]\?\.Invalid" name="warning"/);
  assert.doesNotMatch(source, /skill-warning-icon/);
});

test("internal skill names keep their descenders visible", () => {
  assert.match(source, /\.skill-card__internal-name\s*\{[\s\S]*?line-height:\s*1\.25;/);
});

test("mastered skill equip action slides out only for equipable cards", () => {
  assert.match(source, /'skill-card--equipable':\s*canEquipMasteredSkill\(skill\)/);
  assert.match(source, /class="editor-button editor-button--icon skill-card__equip"/);
  assert.match(source, /\.skill-card__actions\s*\{[\s\S]*?position:\s*absolute;[\s\S]*?transform:\s*translateX\(100%\);[\s\S]*?opacity:\s*0;[\s\S]*?pointer-events:\s*none;/);
  assert.match(source, /\.skill-card--actionable:is\(:hover, :focus-within\) \.skill-card__actions\s*\{[\s\S]*?transform:\s*translateX\(0\);[\s\S]*?opacity:\s*1;[\s\S]*?pointer-events:\s*auto;/);
  assert.match(source, /\.skill-card--equipable\s*\{[\s\S]*?border-right-color:[\s\S]*?box-shadow:/);
  assert.match(source, /\.skill-card--actionable \.skill-card__remove\s*\{[\s\S]*?right:\s*calc\(3rem \+ \.16rem\);/);
  assert.match(source, /@media \(hover:\s*none\)[\s\S]*?\.skill-card--actionable \.skill-card__actions/);
  assert.match(source, /@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*?\.skill-card__actions/);
});
