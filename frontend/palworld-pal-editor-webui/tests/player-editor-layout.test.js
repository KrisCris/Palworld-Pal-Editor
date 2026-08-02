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

const read = path => readFile(new URL(path, import.meta.url), "utf8");

test("player editor uses the shared compact dashboard layout", async () => {
    const source = await read("../src/components/PlayerEditor.vue");
    for (const className of [
        "player-editor", "player-summary", "player-dashboard", "player-panel",
        "player-fields", "status-grid", "technology-panel", "technology-level",
    ]) assert.match(source, new RegExp(`class="[^"]*${className}`), className);
    assert.match(source, /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
    assert.match(source, /@container\s*\(max-width:\s*48rem\)/);
    assert.match(source, /@container\s*\(max-width:\s*32rem\)[\s\S]*\.status-grid\s*\{\s*grid-template-columns:\s*1fr/);
    assert.doesNotMatch(source, /--sub-height|--editor-panel-width|class="PalEditor"|class="EditorItem/);
});

test("technology levels partition normal and ancient lanes without mutating store data", async () => {
    const source = await read("../src/components/PlayerEditor.vue");
    assert.match(source, /const technologyRows\s*=\s*computed\(/);
    assert.match(source, /normal:\s*items\.filter\(item\s*=>\s*!item\.BossTechnology\)/);
    assert.match(source, /ancient:\s*items\.filter\(item\s*=>\s*item\.BossTechnology\)/);
    for (const className of [
        "technology-level__track", "technology-lane--normal", "technology-lane--ancient",
    ]) assert.match(source, new RegExp(`class="[^"]*${className}`), className);
    assert.match(source, /class="technology-level__track"\s*>\s*<h3>/);
    assert.doesNotMatch(source, /items\.(?:sort|splice)\s*\(/);
    assert.match(source, /grid-template-columns:\s*4rem\s+minmax\(7\.5rem,\s*1fr\)\s+max-content/);
    assert.match(source, /@container\s*\(max-width:[^)]+\)[\s\S]*\.technology-lane--ancient\s*\{[\s\S]*grid-column:\s*2/);
});

test("technology lanes render a stable non-mutating partition", async () => {
    const [{ default: PlayerEditor }, { usePalEditorStore }] = await Promise.all([
        loadVueModule("/src/components/PlayerEditor.vue"),
        loadVueModule("/src/stores/paleditor.js"),
    ]);
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = usePalEditorStore();
    store.SELECTED_PLAYER_DATA = {
        NickName: "Tester",
        Level: 1,
        Exp: 0,
        TechnologyPoint: 0,
        bossTechnologyPoint: 0,
        UnusedStatusPoint: 0,
        StatusPoints: {},
        StatusPointMaximums: {},
        UnlockedRecipeTechnologyNames: [],
        toggleTech: () => {},
    };
    const items = [
        { InternalName: "NormalOne", IconAccessKey: "n1", I18n: { Name: "Normal One", Type: "Normal" }, BossTechnology: false },
        { InternalName: "AncientOne", IconAccessKey: "a1", I18n: { Name: "Ancient One", Type: "Ancient" }, BossTechnology: true },
        { InternalName: "NormalTwo", IconAccessKey: "n2", I18n: { Name: "Normal Two", Type: "Normal" }, BossTechnology: false },
    ];
    const originalOrder = items.map(item => item.InternalName);
    store.TECH_LV_DICT = { 1: items };

    const html = await renderVue(PlayerEditor, { pinia });
    const normal = html.match(/technology-lane--normal[^>]*>([\s\S]*?)<\/div><div class="technology-lane technology-lane--ancient/)[1];
    const ancient = html.match(/technology-lane--ancient[^>]*>([\s\S]*?)<\/div><\/section>/)[1];

    assert.ok(normal.indexOf("Normal One") < normal.indexOf("Normal Two"));
    assert.doesNotMatch(normal, /Ancient One/);
    assert.match(ancient, /Ancient One/);
    assert.doesNotMatch(ancient, /Normal (?:One|Two)/);
    assert.deepEqual(items.map(item => item.InternalName), originalOrder);
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

test("technology cards preserve toggle behavior in a compact square control", async () => {
    const source = await read("../src/components/modules/TechCard.vue");
    assert.match(source, /<button type="button"/);
    assert.match(source, /:aria-pressed="!isLocked"/);
    assert.match(source, /:title="`\$\{techName\}: \$\{techState\}`"/);
    assert.match(source, /:disabled="palStore\.LOADING_FLAG"/);
    assert.match(source, /class="[^"]*tech-type/);
    assert.match(source, /class="[^"]*tech-lock/);
    assert.doesNotMatch(source, /\.tech-lock\s*\{[^}]*width:\s*2rem/s);
    assert.match(source, /\.tech-lock\s*\{[^}]*width:\s*max-content[^}]*white-space:\s*normal/s);
    assert.match(source, /inline-size:\s*clamp\(6\.25rem,\s*8vw,\s*7\.5rem\)/);
    assert.match(source, /aspect-ratio:\s*1(?:\s*\/\s*1)?\s*;/);
    assert.match(source, /item\.InternalName/);
    assert.doesNotMatch(source, /item\.internalName/);
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["PlayerEditor_Title", "Editor_Apply_Change", "Editor_Tech_Locked", "Editor_Tech_Unlocked"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});

test("technology toggle dispatch preserves the item name and target lock state", async () => {
    const { toggleTechnology } = await loadVueModule("/src/components/modules/TechCard.vue");
    assert.equal(typeof toggleTechnology, "function");
    const calls = [];
    const player = { toggleTech: (...args) => calls.push(args) };
    const item = { InternalName: "Technology_Test" };

    toggleTechnology(player, item, true);
    toggleTechnology(player, item, false);

    assert.deepEqual(calls, [
        ["Technology_Test", true],
        ["Technology_Test", false],
    ]);
});
