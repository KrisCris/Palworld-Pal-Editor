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
        { value: "Skill_A", label: "Thunder Spear", description: "Electric attack", meta: "exclusive" },
        { value: "Skill_B", label: "Wind Cutter", description: "Leaf attack", meta: "fruit" },
    ];
    assert.deepEqual(filterSearchOptions(options, "thunder"), [options[0]]);
    assert.deepEqual(filterSearchOptions(options, "electric"), [options[0]]);
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
    assert.match(source, /1200/);
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
    assert.doesNotMatch(source, /<select\b/);
    assert.match(editorCss, /\.editor-surface:has\(\.search-select\[open\]\)/);
    for (const handler of ["add_PassiveSkillList", "add_MasteredWaza"]) assert.match(source, new RegExp(handler));
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["Editor_Select_Search", "Editor_Select_No_Results"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
