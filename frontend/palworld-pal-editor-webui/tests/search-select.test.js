import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    closeDisclosureOnOutsidePointer,
    filterSearchOptions,
} from "../src/components/modules/search-select.js";
import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import ja from "../src/i18n/ja.js";
import zhCN from "../src/i18n/zh-CN.js";

const read = path => readFile(new URL(path, import.meta.url), "utf8");

test("searchable options match labels, descriptions, metadata, and internal values", () => {
    const options = [
        { value: "Skill_A", label: "Thunder Spear", description: "Electric attack", meta: "exclusive", searchMeta: "electricity" },
        { value: "Skill_B", label: "Wind Cutter", description: "Leaf attack", meta: "fruit" },
    ];
    assert.deepEqual(filterSearchOptions(options, "thunder"), [options[0]]);
    assert.deepEqual(filterSearchOptions(options, "electric"), [options[0]]);
    assert.deepEqual(filterSearchOptions(options, "electricity"), [options[0]]);
    assert.deepEqual(filterSearchOptions(options, "fruit"), [options[1]]);
    assert.deepEqual(filterSearchOptions(options, "skill_b"), [options[1]]);
    assert.deepEqual(filterSearchOptions(options, ""), options);
    assert.deepEqual(filterSearchOptions(options, "missing"), []);
});

test("an outside pointer closes an open searchable selector", () => {
    const inside = {};
    const disclosure = { open: true, contains: target => target === inside };

    closeDisclosureOnOutsidePointer(disclosure, inside);
    assert.equal(disclosure.open, true);

    closeDisclosureOnOutsidePointer(disclosure, {});
    assert.equal(disclosure.open, false);
});

test("shared selector uses native disclosure, search, and option buttons", async () => {
    const source = await read("../src/components/modules/SearchSelect.vue");
    assert.match(source, /<details/);
    assert.match(source, /type="search"/);
    assert.match(source, /role="listbox"/);
    assert.match(source, /role="option"/);
    assert.match(source, /aria-selected/);
    assert.match(source, /filterSearchOptions/);
    assert.match(source, /emit\('update:modelValue'/);
    assert.match(source, /option\.tooltip/);
    assert.match(source, /class="search-select__tooltip" :aria-hidden="!tooltip"/);
    assert.match(source, /<span v-if="tooltip" role="tooltip">/);
    assert.match(source, /function showTooltip\(option\)\s*\{[\s\S]*?tooltip\.value = option\.tooltip \|\| ''[\s\S]*?\}/);
    assert.doesNotMatch(source, /tooltipTimer|setTimeout/);
});

test("skill options show their internal metadata beside the name before details", async () => {
    const source = await read("../src/components/modules/SearchSelect.vue");
    assert.match(source, /<span class="search-select__title">\s*<strong>{{ option\.label }}<\/strong>\s*<small v-if="option\.meta" class="search-select__meta">{{ option\.meta }}<\/small>\s*<\/span>\s*<small v-if="option\.description">{{ option\.description }}<\/small>/);
});

test("passive skill options are grouped with category headers", async () => {
    const source = await read("../src/components/modules/SearchSelect.vue");
    const editorSource = await read("../src/components/PalEditor.vue");
    assert.match(source, /option\.group/);
    assert.match(source, /search-select__group-label/);
    assert.doesNotMatch(source, /\.search-select__group-label\s*\{[\s\S]*?font-weight\s*:/);
    assert.match(editorSource, /passiveSkillCategoryKey[\s\S]*Editor_Passive_Category_Partner/);
});

test("selector supports keep-open selection, an optional tooltip, and footer actions", async () => {
    const source = await read("../src/components/modules/SearchSelect.vue");
    const editorSource = await read("../src/components/PalEditor.vue");
    const basecampSource = await read("../src/components/BaseCampEditor.vue");
    assert.match(source, /closeOnSelect:\s*\{ type: Boolean, default: true \}/);
    assert.match(source, /showTooltip:\s*\{ type: Boolean, default: true \}/);
    assert.match(source, /if \(props\.closeOnSelect\)\s*\{/);
    assert.match(source, /\$slots\.actions/);
    assert.match(source, /<slot name="actions" \/>/);
    assert.equal((editorSource.match(/:close-on-select="false"/g) || []).length, 3);
    assert.match(editorSource, /ref="skinSelect"/);
    assert.match(editorSource, /const applySkin/);
    assert.match(source, /\.search-select__options button img\s*\{[\s\S]*?object-fit:\s*contain;/);
    assert.doesNotMatch(source, /\.search-select__options button img\s*\{[\s\S]*?border-radius:\s*50%;/);
    assert.doesNotMatch(source, /\.search-select__actions\s*\{[\s\S]*?border-left:/);
    assert.match(basecampSource, /:show-tooltip="false"/);
});

test("Pal editor routes every ordinary dropdown through the searchable selector", async () => {
    const source = await read("../src/components/PalEditor.vue");
    const editorCss = await read("../src/assets/editor-ui.css");
    assert.match(source, /import SearchSelect/);
    assert.match(source, /:options="skinOptions\(\)"/);
    assert.doesNotMatch(source, /<SearchSelect\s+class="editor-control"/);
    assert.match(source, /:options="passiveSkillOptions\(\)"/);
    assert.match(source, /:options="activeSkillSelectOptions\(\)"/);
    assert.match(source, /tooltip:\s*skill\.I18n\[1\]/);
    assert.match(source, /skill\.LearnerNames/);
    assert.equal((source.match(/meta: palStore\.HIDE_INVALID_OPTIONS \? '' : skill\.InternalName/g) || []).length, 2);
    assert.match(source, /searchMeta: skill\.Element/);
    assert.equal((source.match(/activeSkillMetadata\(/g) || []).length, 4);
    assert.match(source, /function activeSkillMetadata\(skill = \{\}\)/);
    assert.match(source, /filter\(badge => badge !== 'exclusive'\)[\s\S]*Editor_Skill_ATK[\s\S]*Editor_Skill_CD[\s\S]*badges\.includes\('exclusive'\)[\s\S]*skill\.LearnerNames\.join\(' \/ '\)/);
    assert.doesNotMatch(source, /<select\b/);
    assert.match(source, /\.skill-card__identity \{[\s\S]*?gap: 0;/);
    assert.match(source, /\.skill-card__internal-name \{[\s\S]*?opacity: \.55;/);
    assert.match(source, /\.skill-card__identity strong,[\s\S]*?white-space: nowrap;/);
    assert.doesNotMatch(source, /class="skill-warning"/);
    assert.match(editorCss, /\.editor-surface:has\(\.search-select\[open\]\)/);
    // Both pickers keep an add button in the slot. Their names used to be RPC
    // action names; they are the store actions now.
    for (const handler of ["addPassiveSkill", "addActiveSkill"]) assert.match(source, new RegExp(`@click="${handler}"`));
    assert.equal((source.match(/class="skill-card__title"/g) || []).length, 3);
    assert.equal((source.match(/<small v-if="!palStore\.HIDE_INVALID_OPTIONS" class="skill-card__internal-name">{{ skill }}<\/small>/g) || []).length, 3);
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["Editor_Select_Search", "Editor_Select_No_Results"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
