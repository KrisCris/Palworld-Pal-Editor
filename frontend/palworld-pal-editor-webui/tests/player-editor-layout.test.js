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
        "player-fields", "player-stats", "effigy-panel", "effigy-grid",
        "technology-panel", "technology-level",
    ]) assert.match(source, new RegExp(`class="[^"]*${className}`), className);
    assert.match(source, /\.player-dashboard\s*\{[^}]*grid-template-columns:\s*minmax\(18rem,\s*\.75fr\)\s+minmax\(28rem,\s*1\.25fr\)/s);
    assert.match(source, /\.effigy-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/s);
    assert.match(source, /\.status-control header \.status-name\s*\{\s*flex:\s*1;/);
    assert.match(source, /@container\s*\(max-width:\s*48rem\)/);
    assert.match(source, /@container\s*\(max-width:\s*32rem\)[\s\S]*\.effigy-grid\s*\{\s*grid-template-columns:\s*1fr/);
    assert.doesNotMatch(source, /--sub-height|--editor-panel-width|class="PalEditor"|class="EditorItem/);
});

test("stat allocation preview refunds blue levels and spends unused points first", async () => {
    const { previewStatAllocation } = await loadVueModule("/src/components/PlayerEditor.vue");
    const player = {
        StatusPoints: { "最大HP": 20 },
        ExStatusPoints: { "最大HP": 30 },
        UnusedStatusPoint: 7,
        StatusPointTotalMaximums: { "最大HP": 50 },
    };

    assert.deepEqual(previewStatAllocation(player, "最大HP", 45), {
        stat: 15, item: 30, unused: 12, total: 45,
    });
    assert.deepEqual(previewStatAllocation(player, "最大HP", 10), {
        stat: 0, item: 10, unused: 27, total: 10,
    });

    const lowerPlayer = {
        StatusPoints: { "最大HP": 20 },
        ExStatusPoints: { "最大HP": 20 },
        UnusedStatusPoint: 5,
        StatusPointTotalMaximums: { "最大HP": 50 },
    };
    assert.deepEqual(previewStatAllocation(lowerPlayer, "最大HP", 50), {
        stat: 25, item: 25, unused: 0, total: 50,
    });
    assert.deepEqual(player, {
        StatusPoints: { "最大HP": 20 },
        ExStatusPoints: { "最大HP": 30 },
        UnusedStatusPoint: 7,
        StatusPointTotalMaximums: { "最大HP": 50 },
    });
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
    assert.match(source, /\.technology-level__track\s*\{[^}]*place-items:\s*center;/s);
});

test("technology lanes render a stable non-mutating partition", async () => {
    const [
        { default: PlayerEditor }, { usePalEditorStore }, { usePlayersStore },
        { useRostersStore }, { useCatalogsStore },
    ] = await Promise.all([
        loadVueModule("/src/components/PlayerEditor.vue"),
        loadVueModule("/src/stores/paleditor.js"),
        loadVueModule("/src/stores/players.js"),
        loadVueModule("/src/stores/rosters.js"),
        loadVueModule("/src/stores/catalogs.js"),
    ]);
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = usePalEditorStore();
    usePlayersStore().playersByUid = new Map([["player-1", {
        NickName: "Tester",
        Level: 1,
        Exp: 0,
        TechnologyPoint: 0,
        bossTechnologyPoint: 0,
        UnusedStatusPoint: 0,
        StatusPoints: { "最大HP": 14 },
        ExStatusPoints: { "最大HP": 12 },
        StatusPointTotals: { "最大HP": 26 },
        StatusPointMinimums: { "最大HP": 0 },
        StatusPointMaximums: { "最大HP": 38 },
        StatusPointTotalMaximums: { "最大HP": 50 },
        StatusPointMetadata: {
            "最大HP": { category: "stat", icon: "stat-health", unit: "flat", values: Array.from({ length: 51 }, (_, rank) => rank * 100) },
        },
        UnlockedRecipeTechnologyNames: [],
    }]]);
    useRostersStore().activeRosterKey = "player:player-1";
    const items = [
        { InternalName: "NormalOne", IconAccessKey: "n1", I18n: { Name: "Normal One", Type: "Normal" }, BossTechnology: false },
        { InternalName: "AncientOne", IconAccessKey: "a1", I18n: { Name: "Ancient One", Type: "Ancient" }, BossTechnology: true },
        { InternalName: "NormalTwo", IconAccessKey: "n2", I18n: { Name: "Normal Two", Type: "Normal" }, BossTechnology: false },
    ];
    const originalOrder = items.map(item => item.InternalName);
    useCatalogsStore().technologiesByLevel = { 1: items };

    const html = await renderVue(PlayerEditor, { pinia });
    const normal = html.match(/technology-lane--normal[^>]*>([\s\S]*?)<\/div><div class="technology-lane technology-lane--ancient/)[1];
    const ancient = html.match(/technology-lane--ancient[^>]*>([\s\S]*?)<\/div><\/section>/)[1];

    assert.ok(normal.indexOf("Normal One") < normal.indexOf("Normal Two"));
    assert.doesNotMatch(normal, /Ancient One/);
    assert.match(ancient, /Ancient One/);
    assert.doesNotMatch(ancient, /Normal (?:One|Two)/);
    assert.match(html, /image\/ui\/stat-health/);
    assert.match(html, /26 \/ 50/);
    assert.match(html, /\+2600/);
    assert.deepEqual(items.map(item => item.InternalName), originalOrder);
});

test("player controls preserve every update contract", async () => {
    const source = await read("../src/components/PlayerEditor.vue");
    for (const field of ["NickName", "TechnologyPoint", "bossTechnologyPoint", "UnusedStatusPoint"]) {
        assert.match(source, new RegExp(`name="${field}"`), field);
    }
    for (const handler of [
        "palStore.updatePlayer", "playerLevelDown", "playerLevelUp", "playerMaxLevel",
        "setStatusPoint(name)", "palStore.unlockAllTechs",
    ]) assert.match(source, new RegExp(handler.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), handler);
    assert.match(source, /<SegmentedRange/);
    assert.doesNotMatch(source, /<input[^>]+type="range"/);
    assert.match(source, /StatusPointTotalMaximums\[name\]/);
    assert.match(source, /StatusPointTotals\[name\]/);
    assert.match(source, /@change="palStore\.setStatusPoint\(name\)"/);
    assert.match(source, /:aria-label="fieldActionLabel/);
});

test("status sliders dispatch stat totals separately from effigy ranks", async () => {
    const source = await read("../src/stores/paleditor.js");
    assert.match(source, /category === "stat"[\s\S]*\? "StatusPointTotals"[\s\S]*: "StatusPoints"/);
    assert.match(source, /Math\.max\(Math\.trunc\(points\), player\.StatusPointMinimums\[name\] \?\? 0\)/);
    assert.match(source, /player\.StatusPointTotalMaximums\[name\] \?\? 0/);
});

test("stat source labels are translated in every UI locale", () => {
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["Editor_StatPoints", "Editor_ItemLevel"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
    assert.equal(en.Editor_UnusedStatusPoints, "Unused Stat Points");
});

test("technology cards preserve toggle behavior in a compact square control", async () => {
    const source = await read("../src/components/TechCard.vue");
    assert.match(source, /<button type="button"/);
    assert.match(source, /:aria-pressed="!isLocked"/);
    assert.match(source, /:title="`\$\{techName\}: \$\{techState\}`"/);
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
    const { toggleTechnology } = await loadVueModule("/src/components/TechCard.vue");
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

test("technology cards match save keys without case sensitivity", async () => {
    const { hasUnlockedTechnology } = await loadVueModule("/src/components/TechCard.vue");

    assert.equal(hasUnlockedTechnology(["PalBox"], "PALBOX"), true);
    assert.equal(hasUnlockedTechnology(["OverHeatRifle"], "OverheatRifle"), true);
    assert.equal(hasUnlockedTechnology(["ShotgunBullet"], "ShotGunBullet"), true);
    assert.equal(hasUnlockedTechnology(["PalBox"], "Snowman"), false);
});
