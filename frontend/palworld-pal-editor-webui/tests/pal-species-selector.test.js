import assert from "node:assert/strict";
import test from "node:test";

import {
    buildPalFamilies,
    formatPaldeck,
    hasVisibleVariant,
    matchesPalQuery,
    moveListboxIndex,
    paldeckForRow,
    palLabel,
} from "../src/components/modules/pal-species-selector.js";

const locales = await Promise.all([
    import("../src/i18n/en.js"),
    import("../src/i18n/fr.js"),
    import("../src/i18n/ja.js"),
    import("../src/i18n/zh-CN.js"),
]);

const rows = [
    {
        InternalName: "SheepBall",
        FamilyID: "SheepBall",
        VariantKind: "base",
        VariantTags: ["base"],
        I18n: "Lamball",
        SortingKey: "001",
        IconKey: "SheepBall",
        Invalid: false,
    },
    {
        InternalName: "BOSS_SheepBall",
        FamilyID: "SheepBall",
        VariantKind: "alpha",
        VariantTags: ["alpha", "boss"],
        I18n: "Alpha Lamball",
        SortingKey: "001",
        IconKey: "SheepBall",
        Invalid: false,
    },
    {
        InternalName: "GYM_SheepBall",
        FamilyID: "SheepBall",
        VariantKind: "tower",
        VariantTags: ["tower"],
        I18n: "Tower Lamball",
        SortingKey: "001",
        IconKey: "SheepBall",
        Invalid: true,
    },
    {
        InternalName: "BOSS_ElecPanda_BossRush",
        FamilyID: "ElecPanda",
        VariantKind: "boss-rush",
        VariantTags: ["boss-rush", "tower"],
        I18n: "Highly Modified Grizzbolt",
        SortingKey: "103",
        IconKey: "ElecPanda",
        Invalid: true,
    },
    {
        InternalName: "Hunter_Rifle",
        FamilyID: "Hunter_Rifle",
        VariantKind: "human",
        VariantTags: ["human"],
        I18n: "Syndicate Gunner",
        SortingKey: "",
        IconKey: "Hunter_Bat",
        IsHuman: true,
        Invalid: false,
    },
];

test("groups variants without mutation and orders the base before special kinds", () => {
    const snapshot = structuredClone(rows);
    const families = buildPalFamilies(rows, "BOSS_SheepBall", false, "");
    const sheep = families.find(family => family.FamilyID === "SheepBall");

    assert.equal(sheep.Name, "Lamball");
    assert.equal(sheep.Paldeck, "001");
    assert.deepEqual(
        sheep.variants.map(variant => variant.InternalName),
        ["SheepBall", "BOSS_SheepBall", "GYM_SheepBall"],
    );
    assert.equal(sheep.variants[1].current, true);
    assert.equal(sheep.variants[2].warning, true);
    assert.deepEqual(rows, snapshot);
});

test("matches localized names and exact, family, and Paldeck identifiers", () => {
    const family = {
        FamilyID: "SheepBall",
        Name: "Lamball",
        Paldeck: "001",
    };
    const variant = rows[1];

    for (const query of ["lamb", "BOSS_SHEEP", "sheepball", "001"]) {
        assert.equal(matchesPalQuery(family, variant, query), true, query);
    }
    assert.equal(matchesPalQuery(family, variant, "grizzbolt"), false);
});

test("a matching variant retains its family in filtered results", () => {
    const families = buildPalFamilies(rows, "SheepBall", false, "tower lamball");

    assert.deepEqual(families.map(family => family.FamilyID), ["SheepBall"]);
    assert.deepEqual(
        families[0].variants.map(variant => variant.InternalName),
        ["GYM_SheepBall"],
    );
});

test("hidden invalid variants stay hidden except for the current exact ID", () => {
    const hidden = buildPalFamilies(rows, "SheepBall", true, "");
    const sheep = hidden.find(family => family.FamilyID === "SheepBall");
    assert.deepEqual(
        sheep.variants.map(variant => variant.InternalName),
        ["SheepBall", "BOSS_SheepBall"],
    );
    assert.equal(hidden.some(family => family.FamilyID === "ElecPanda"), false);

    const retained = buildPalFamilies(rows, "BOSS_ElecPanda_BossRush", true, "");
    const currentFamily = retained.find(family => family.FamilyID === "ElecPanda");
    assert.deepEqual(
        currentFamily.variants.map(variant => variant.InternalName),
        ["BOSS_ElecPanda_BossRush"],
    );
    assert.equal(currentFamily.variants[0].current, true);
    assert.equal(currentFamily.variants[0].warning, true);
});

test("cheat options reveal and warn invalid-only families", () => {
    const families = buildPalFamilies(rows, "SheepBall", false, "");
    const invalidOnly = families.find(family => family.FamilyID === "ElecPanda");

    assert.equal(invalidOnly.invalidOnly, true);
    assert.equal(invalidOnly.variants[0].warning, true);
});

test("object rows and humans produce single-member families with exact values", () => {
    const humans = [
        rows[4],
        {
            ...rows[4],
            InternalName: "Hunter_Bat",
            I18n: "Syndicate Thug",
        },
    ];
    const asObject = Object.fromEntries(humans.map(row => [row.InternalName, row]));
    const families = buildPalFamilies(asObject, "Hunter_Rifle", true, "");

    assert.equal(families.length, 2);
    assert.deepEqual(
        families.flatMap(family => family.variants.map(row => row.InternalName)).sort(),
        ["Hunter_Bat", "Hunter_Rifle"],
    );
    assert.equal(
        families.find(family => family.FamilyID === "Hunter_Rifle").variants[0].current,
        true,
    );
});

test("families without a Paldeck number sort after numbered Pals", () => {
    const families = buildPalFamilies([
        rows[0],
        {
            InternalName: "UnknownPal",
            FamilyID: "UnknownPal",
            VariantKind: "base",
            VariantTags: ["base"],
            I18n: "Unknown Pal",
            SortingKey: "",
            Invalid: false,
        },
    ], "SheepBall", true, "");

    assert.deepEqual(families.map(family => family.FamilyID), ["SheepBall", "UnknownPal"]);
});

test("only a variant visible in the active family can be applied", () => {
    const families = buildPalFamilies(rows, "SheepBall", false, "");
    const sheep = families.find(family => family.FamilyID === "SheepBall");
    const elecPanda = families.find(family => family.FamilyID === "ElecPanda");

    assert.equal(hasVisibleVariant(sheep, "BOSS_SheepBall"), true);
    assert.equal(hasVisibleVariant(sheep, "BOSS_ElecPanda_BossRush"), false);
    assert.equal(hasVisibleVariant(elecPanda, "BOSS_ElecPanda_BossRush"), true);
    assert.equal(hasVisibleVariant(undefined, "BOSS_ElecPanda_BossRush"), false);
});

test("listbox navigation handles arrows, Home, and End without leaving its options", () => {
    assert.equal(moveListboxIndex(1, 4, "ArrowDown"), 2);
    assert.equal(moveListboxIndex(3, 4, "ArrowDown"), 0);
    assert.equal(moveListboxIndex(0, 4, "ArrowUp"), 3);
    assert.equal(moveListboxIndex(2, 4, "Home"), 0);
    assert.equal(moveListboxIndex(1, 4, "End"), 3);
    assert.equal(moveListboxIndex(-1, 4, "ArrowDown"), 0);
    assert.equal(moveListboxIndex(0, 0, "ArrowDown"), -1);
});

test("Paldeck numbers keep the existing three-digit display format", () => {
    assert.equal(formatPaldeck(""), "");
    assert.equal(formatPaldeck("1"), "001");
    assert.equal(formatPaldeck("77"), "077");
    assert.equal(formatPaldeck("102B"), "102B");
    assert.equal(formatPaldeck("unknown"), "unknown");
    assert.equal(paldeckForRow({ SortingKey: "", PaldeckRecordID: "InternalFamilyKey" }), "");
    assert.equal(palLabel({ SortingKey: "", I18n: "Unknown Pal" }), "Unknown Pal");
    assert.equal(palLabel({ SortingKey: "7", I18n: "Tanzee" }), "007 Tanzee");
});

test("selector UI labels exist in every supported UI locale", () => {
    const keys = [
        "Editor_Pal_Selector_Title",
        "Editor_Pal_Selector_Select",
        "Editor_Pal_Selector_Search",
        "Editor_Pal_Selector_Search_Placeholder",
        "Editor_Pal_Selector_Families",
        "Editor_Pal_Selector_Variants",
        "Editor_Pal_Selector_Warning",
        "Editor_Pal_Selector_No_Results",
        "Editor_Pal_Selector_Apply",
    ];
    for (const { default: locale } of locales) {
        for (const key of keys) assert.equal(typeof locale[key], "string", key);
    }
});
