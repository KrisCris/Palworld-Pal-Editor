import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { filterSearchOptions } from "../src/components/modules/search-select.js";
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

test("shared selector uses native disclosure, search, and option buttons", async () => {
    const source = await read("../src/components/modules/SearchSelect.vue");
    assert.match(source, /<details/);
    assert.match(source, /type="search"/);
    assert.match(source, /role="listbox"/);
    assert.match(source, /role="option"/);
    assert.match(source, /aria-selected/);
    assert.match(source, /filterSearchOptions/);
    assert.match(source, /emit\('update:modelValue'/);
});

test("Pal editor routes every ordinary dropdown through the searchable selector", async () => {
    const source = await read("../src/components/PalEditor.vue");
    assert.match(source, /import SearchSelect/);
    assert.match(source, /:options="skinOptions\(\)"/);
    assert.match(source, /:options="passiveSkillOptions\(\)"/);
    assert.match(source, /:options="activeSkillSelectOptions\(\)"/);
    assert.doesNotMatch(source, /<select\b/);
    for (const handler of ["add_PassiveSkillList", "add_MasteredWaza"]) assert.match(source, new RegExp(handler));
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["Editor_Select_Search", "Editor_Select_No_Results"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
