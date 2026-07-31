import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";

import { createPinia, setActivePinia } from "pinia";

import { skillBadges, usePalEditorStore } from "../src/stores/paleditor.js";

globalThis.localStorage ??= {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
};

const sourceRoots = [
    new URL("../src/", import.meta.url),
    new URL("../public/", import.meta.url),
];
const emoji = /\p{Extended_Pictographic}|\p{Regional_Indicator}|[\uFE0F\u20E3]/u;

async function sourcesBelow(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    const sources = [];
    for (const entry of entries) {
        const url = new URL(entry.name + (entry.isDirectory() ? "/" : ""), directory);
        if (entry.isDirectory()) {
            sources.push(...await sourcesBelow(url));
        } else if (/\.(?:vue|js|css|html|md)$/.test(entry.name)) {
            sources.push([url.pathname, await readFile(url, "utf8")]);
        }
    }
    return sources;
}

async function frontendSources() {
    const sources = (await Promise.all(sourceRoots.map(sourcesBelow))).flat();
    const indexUrl = new URL("../index.html", import.meta.url);
    sources.push([indexUrl.pathname, await readFile(indexUrl, "utf8")]);
    return sources;
}

test("presentation helpers return asset keys and CSS tiers instead of glyphs", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    assert.equal(typeof store.elementIconKey, "function");
    assert.equal(store.elementIconKey("Leaf"), "Grass");
    assert.equal(store.elementIconKey("Earth"), "Ground");
    assert.equal(store.elementIconKey("Electricity"), "Electric");
    assert.equal(store.elementIconKey("Normal"), "Neutral");
    assert.equal(store.elementIconKey("Fire"), "Fire");
    assert.equal(store.elementIconKey("None"), null);
    assert.equal(store.elementIconKey("Unknown"), null);

    assert.equal(store.passiveTier(5), "top");
    assert.equal(store.passiveTier(4), "high");
    assert.equal(store.passiveTier(2), "positive");
    assert.equal(store.passiveTier(1), "neutral");
    assert.equal(store.passiveTier(-1), "negative");
    assert.deepEqual(skillBadges({ BossSkill: true }), ["boss"]);
    assert.equal(store.skillBadgeTranslationKey("boss"), "Editor_Skill_Badge_Boss");
    assert.equal(store.genderKey("EPalGenderType::Female"), "female");
    assert.equal(store.genderKey("EPalGenderType::Male"), "male");
    assert.equal(store.genderKey("NONE"), null);
    assert.deepEqual(
        store.specialTypeKeys({ IsBOSS: true, IsRarePal: true }),
        ["boss", "rare"],
    );
    assert.deepEqual(store.specialTypeKeys({}), []);
});

test("Pal element helpers return canonical keys for image rendering", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    store.PAL_STATIC_DATA = {
        TestPal: { Elements: ["Leaf", "Earth"] },
    };

    assert.deepEqual(store.palElementKeys("TestPal"), ["Grass", "Ground"]);
    assert.deepEqual(store.palElementKeys("MissingPal"), []);
});

test("the complete frontend source is emoji-free", async () => {
    for (const [name, source] of await frontendSources()) {
        assert.equal(emoji.test(source), false, name);
    }
});

test("the local SVG icon renderer and sprite are available", async () => {
    const [component, sprite] = await Promise.all([
        readFile(new URL("../src/components/modules/UiIcon.vue", import.meta.url), "utf8"),
        readFile(new URL("../src/assets/ui-icons.svg", import.meta.url), "utf8"),
    ]);

    assert.match(component, /<use\s+:href=/);
    assert.match(component, /pointer-events:\s*none/);
    for (const icon of [
        "save", "refresh", "home", "more", "language", "search", "plus",
        "minus", "maximum", "check", "close", "delete", "copy", "export",
        "folder", "file", "back", "forward", "unlock", "warning", "eye",
    ]) {
        assert.match(sprite, new RegExp(`<symbol\\s+id=["']${icon}["']`), icon);
    }
});

test("game UI image routes omit extensions and icon-only controls are named", async () => {
    const sources = Object.fromEntries(await frontendSources());
    for (const [name, source] of Object.entries(sources)) {
        assert.doesNotMatch(source, /\/image\/ui\/[^\s'"`]+\.png/, name);
    }
    const iconButton = await readFile(
        new URL("../src/components/modules/IconButton.vue", import.meta.url),
        "utf8",
    );
    const pathPicker = await readFile(
        new URL("../src/components/PathPicker.vue", import.meta.url),
        "utf8",
    );
    assert.match(iconButton, /:aria-label="label"/);
    assert.match(pathPicker, /PathPicker_Back/);
    assert.match(pathPicker, /PathPicker_Open/);
});
