import assert from "node:assert/strict";
import test from "node:test";

import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { watch } from "vue";

import {
    canToggleBossVariant,
    filterSkillOptions,
    isSkillAssignable,
    skillBadges,
    usePalEditorStore,
} from "../src/stores/paleditor.js";

test("boss toggles require both a base and boss family member", () => {
    assert.equal(canToggleBossVariant({ HasBaseVariant: true, HasBossVariant: true }), true);
    assert.equal(canToggleBossVariant({ HasBaseVariant: false, HasBossVariant: true }), false);
});

const storage = new Map();
globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
};

const locales = await Promise.all([
    import("../src/i18n/en.js"),
    import("../src/i18n/fr.js"),
    import("../src/i18n/ja.js"),
    import("../src/i18n/zh-CN.js"),
]);

test("skill badges are derived only from endpoint metadata", () => {
    assert.deepEqual(skillBadges({}), []);
    assert.deepEqual(skillBadges({ NonInheritable: true }), ["nonInheritable"]);
    assert.deepEqual(skillBadges({ Exclusive: true }), ["exclusive"]);
    assert.deepEqual(skillBadges({ BossSkill: true }), ["boss"]);
    assert.deepEqual(skillBadges({ HasSkillFruit: true }), ["fruit"]);
    assert.deepEqual(skillBadges({ SkillFruit: true }), ["fruit"]);
    assert.deepEqual(skillBadges({ Assignable: false }), ["disabled"]);
    assert.deepEqual(
        skillBadges({ Assignable: false, AssignableToHumans: true }, true),
        [],
    );
    assert.deepEqual(skillBadges({ Disabled: true }), ["disabled"]);
    assert.deepEqual(
        skillBadges({
            NonInheritable: true,
            Exclusive: true,
            BossSkill: true,
            HasSkillFruit: true,
            Assignable: false,
        }),
        ["nonInheritable", "exclusive", "boss", "fruit", "disabled"],
    );
});

test("skill filtering is stable, exact, non-mutating, and tolerant of missing current IDs", () => {
    const skills = [
        { InternalName: "normal", Invalid: false, Assignable: true },
        { InternalName: "current-invalid", Invalid: true, Assignable: false },
        { InternalName: "current-invalid-family", Invalid: true, Assignable: false },
        {
            InternalName: "EPalWazaID::Human_Punch",
            Invalid: false,
            Assignable: false,
            AssignableToHumans: true,
        },
    ];
    const snapshot = structuredClone(skills);

    assert.deepEqual(filterSkillOptions(skills, undefined, true), [skills[0]]);
    assert.deepEqual(filterSkillOptions(skills, ["current-invalid"], true), [
        skills[0],
        skills[1],
    ]);
    assert.deepEqual(
        filterSkillOptions(skills, ["current-invalid-family-extra"], true),
        [skills[0]],
    );
    assert.deepEqual(filterSkillOptions(skills, [], false), skills);
    assert.deepEqual(filterSkillOptions(undefined, undefined, true), []);
    assert.deepEqual(skills, snapshot);

    assert.equal(
        filterSkillOptions(skills, [], true).some(
            skill => skill.InternalName === "EPalWazaID::Human_Punch",
        ),
        false,
    );
    assert.deepEqual(filterSkillOptions(skills, ["EPalWazaID::Human_Punch"], true), [
        skills[0],
        skills[3],
    ]);
    assert.deepEqual(filterSkillOptions(skills, [], true, true), [skills[3]]);
    assert.equal(isSkillAssignable(skills[0], false), true);
    assert.equal(isSkillAssignable(skills[0], true), false);
    assert.equal(isSkillAssignable(skills[3], true), true);

    const retainedInvalid = filterSkillOptions(
        skills,
        ["current-invalid"],
        true,
    ).find(skill => skill.InternalName === "current-invalid");
    assert.equal(retainedInvalid.Invalid, true);
    assert.deepEqual(skillBadges(retainedInvalid), ["disabled"]);
});

test("game element enums and passive tiers use stable presentation keys", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    assert.equal(typeof store.elementIconKey, "function");
    assert.equal(store.elementIconKey("Leaf"), "Grass");
    assert.equal(store.elementIconKey("Earth"), "Ground");
    assert.equal(store.elementIconKey("Electricity"), "Electric");
    assert.equal(store.elementIconKey("Normal"), "Neutral");
    assert.equal(store.passiveTier(5), "top");
    assert.equal(store.passiveTier(4), "high");
    assert.equal(store.passiveTier(2), "positive");
});

test("skill metadata labels and non-assignable warning exist in every UI locale", () => {
    const keys = [
        "Editor_Skill_Badge_NonInheritable",
        "Editor_Skill_Badge_Exclusive",
        "Editor_Skill_Badge_Boss",
        "Editor_Skill_Badge_Fruit",
        "Editor_Skill_Badge_Disabled",
        "Message_Skill_Not_Assignable",
        "Editor_Variant_tower",
        "Editor_Variant_boss",
        "Editor_Variant_rare",
        "Editor_Variant_raid",
        "Editor_Variant_predator",
        "Editor_Variant_oilrig",
        "PathPicker_Back",
        "PathPicker_Open",
    ];
    for (const { default: locale } of locales) {
        for (const key of keys) assert.equal(typeof locale[key], "string", key);
    }
});

test("public updatePal blocks non-assignable skill additions before loading or PATCH", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    store.ACTIVE_SKILLS = {
        [humanPunch]: {
            InternalName: humanPunch,
            Invalid: false,
            Assignable: false,
        },
    };
    store.SELECTED_PAL_DATA = { IsHuman: false };

    const patchCalls = [];
    const originalPatch = axios.patch;
    axios.patch = async (...args) => {
        patchCalls.push(args);
        return { data: { status: 0, data: null, msg: null } };
    };
    const loadingChanges = [];
    const stopWatching = watch(
        () => store.LOADING_FLAG,
        value => loadingChanges.push(value),
        { flush: "sync" },
    );
    t.after(() => {
        stopWatching();
        axios.patch = originalPatch;
    });

    for (const name of ["add_MasteredWaza", "add_EquipWaza"]) {
        await store.updatePal({ target: { name, value: humanPunch } });
    }

    assert.deepEqual(patchCalls, []);
    assert.equal(store.LOADING_FLAG, false);
    assert.deepEqual(loadingChanges, []);
});

test("public updatePal allows human-only skills for a selected human", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    store.ACTIVE_SKILLS = {
        [humanPunch]: {
            InternalName: humanPunch,
            Invalid: false,
            Assignable: false,
            AssignableToHumans: true,
        },
    };
    store.SELECTED_PAL_DATA = { IsHuman: true };

    const patchCalls = [];
    const originalPatch = axios.patch;
    axios.patch = async (url, payload) => {
        patchCalls.push([url, payload]);
        return { data: { status: 0, data: null, msg: null } };
    };
    t.after(() => { axios.patch = originalPatch; });

    await store.updatePal({
        target: { name: "add_MasteredWaza", value: humanPunch },
    });

    assert.equal(patchCalls.length, 1);
    assert.equal(patchCalls[0][1].value, humanPunch);
});

test("public updatePal still sends removals and unrelated updates", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    store.ACTIVE_SKILLS = {
        [humanPunch]: {
            InternalName: humanPunch,
            Invalid: false,
            Assignable: false,
        },
    };

    const patchCalls = [];
    const originalPatch = axios.patch;
    axios.patch = async (url, payload) => {
        patchCalls.push([url, payload]);
        return { data: { status: 0, data: null, msg: null } };
    };
    t.after(() => { axios.patch = originalPatch; });

    for (const target of [
        { name: "pop_MasteredWaza", value: humanPunch },
        { name: "pop_EquipWaza", value: humanPunch },
        { name: "NickName", value: "ordinary update" },
        { name: "unknown_operation", value: "unchanged passthrough" },
    ]) {
        await store.updatePal({ target });
    }

    assert.deepEqual(
        patchCalls.map(([url, payload]) => [url, payload.key, payload.value]),
        [
            ["/api/pal/paldata", "pop_MasteredWaza", humanPunch],
            ["/api/pal/paldata", "pop_EquipWaza", humanPunch],
            ["/api/pal/paldata", "NickName", "ordinary update"],
            ["/api/pal/paldata", "unknown_operation", "unchanged passthrough"],
        ],
    );
    assert.equal(store.LOADING_FLAG, false);
});
