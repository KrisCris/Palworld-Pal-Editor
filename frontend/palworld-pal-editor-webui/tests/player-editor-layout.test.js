import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import ja from "../src/i18n/ja.js";
import zhCN from "../src/i18n/zh-CN.js";

const read = path => readFile(new URL(path, import.meta.url), "utf8");

test("player editor uses the shared compact dashboard layout", async () => {
    const source = await read("../src/components/PlayerEditor.vue");
    for (const className of [
        "player-editor", "player-summary", "player-dashboard", "player-panel",
        "player-fields", "status-grid", "technology-panel", "technology-level",
    ]) assert.match(source, new RegExp(`class="[^"]*${className}`), className);
    assert.match(source, /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
    assert.match(source, /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(7rem,\s*1fr\)\)/);
    assert.match(source, /@container\s*\(max-width:\s*48rem\)/);
    assert.match(source, /@container\s*\(max-width:\s*32rem\)[\s\S]*\.status-grid\s*\{\s*grid-template-columns:\s*1fr/);
    assert.doesNotMatch(source, /--sub-height|--editor-panel-width|class="PalEditor"|class="EditorItem/);
});

test("player controls preserve every update contract", async () => {
    const source = await read("../src/components/PlayerEditor.vue");
    for (const field of ["NickName", "TechnologyPoint", "bossTechnologyPoint", "UnusedStatusPoint"]) {
        assert.match(source, new RegExp(`name="${field}"`), field);
    }
    for (const handler of [
        "palStore.updatePlayer", "levelDown", "levelUp", "maxLevel",
        "setStatusPoint(name)", "unlock_all_techs",
    ]) assert.match(source, new RegExp(handler.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), handler);
    assert.match(source, /:max="palStore\.SELECTED_PLAYER_DATA\.StatusPointMaximums\[name\]"/);
    assert.match(source, /:aria-label="fieldActionLabel/);
});

test("technology cards expose a visible localized lock state", async () => {
    const source = await read("../src/components/modules/TechCard.vue");
    assert.match(source, /<button type="button"/);
    assert.match(source, /:aria-pressed="!isLocked"/);
    assert.match(source, /class="tech-state"/);
    assert.match(source, /item\.InternalName/);
    assert.doesNotMatch(source, /item\.internalName/);
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["PlayerEditor_Title", "Editor_Apply_Change", "Editor_Tech_Locked", "Editor_Tech_Unlocked"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
