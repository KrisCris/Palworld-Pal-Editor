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
import { useAppStore } from "../src/stores/app.js";
import { useCatalogsStore } from "../src/stores/catalogs.js";
import { usePalsStore } from "../src/stores/pals.js";
import { useSessionStore } from "../src/stores/session.js";

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

// Spec §8.3's operation result. These cases are about what the store sends, so
// the record it answers with is the one already in the cache.
const operation = () => ({
    resultRecord: null,
    deletedRecordKeys: [],
    affectedRosterKeys: [],
    affectedStorageKeys: [],
});

function selectPal(pal) {
    const pals = usePalsStore();
    pals.applyDetail({ recordKey: "world:selected", EquipWaza: [], MasteredWaza: [], ...pal });
    pals.selectedRecordKey = "world:selected";
}

// The two ways the editor adds an active skill: the dropdown under the mastered
// list, and the pick list beside the equipped slots.
function learnSkill(store, skill) {
    store.PAL_ACTIVE_SELECTED_ITEM = skill;
    return store.addMasteredWaza();
}

const equipSkill = (store, skill) => store.addEquipWaza({ target: { name: skill } });

// Every skill write is a PUT of the whole list; these record what was sent.
function recordSkillWrites(t) {
    const writes = [];
    const originalPut = axios.put;
    axios.put = async (url, body) => {
        writes.push([url, body.skills]);
        return { data: operation() };
    };
    t.after(() => { axios.put = originalPut; });
    return writes;
}

test("adding a non-assignable skill is refused before any request", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    useCatalogsStore().activeSkills = [{
        InternalName: humanPunch,
        Invalid: false,
        Assignable: false,
    }];
    selectPal({ IsHuman: false });
    const writes = recordSkillWrites(t);

    await learnSkill(store, humanPunch);
    await equipSkill(store, humanPunch);

    assert.deepEqual(writes, []);
    assert.equal(useSessionStore().operationPending, false);
});

test("cheat mode allows a known skill the game would not assign", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const skillId = "EPalWazaID::Cheat_Test";
    useCatalogsStore().activeSkills = [{
        InternalName: skillId,
        Invalid: true,
        Disabled: true,
        Assignable: false,
    }];
    selectPal({ IsHuman: false });
    useAppStore().HIDE_INVALID_OPTIONS = false;
    const writes = recordSkillWrites(t);

    await learnSkill(store, skillId);
    await equipSkill(store, skillId);

    // Learning a move with an active slot free equips it too, so both go to the
    // equipped list -- which is also what learns them.
    assert.deepEqual(writes.map(([url]) => url.split("/skills/")[1]), [
        "equipped",
        "equipped",
    ]);
    assert.deepEqual(writes[0][1], [skillId]);
});

test("a skill no catalog knows is refused even in cheat mode", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    useCatalogsStore().activeSkills = [];
    selectPal({ IsHuman: false });
    useAppStore().HIDE_INVALID_OPTIONS = false;
    const writes = recordSkillWrites(t);

    await learnSkill(store, "EPalWazaID::Unknown");
    await equipSkill(store, "EPalWazaID::Unknown");

    assert.deepEqual(writes, []);
    assert.equal(useSessionStore().operationPending, false);
});

test("a human-only skill is assignable to a selected human", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    useCatalogsStore().activeSkills = [{
        InternalName: humanPunch,
        Invalid: false,
        Assignable: false,
        AssignableToHumans: true,
    }];
    selectPal({ IsHuman: true });
    const writes = recordSkillWrites(t);

    await learnSkill(store, humanPunch);

    assert.equal(writes.length, 1);
    assert.deepEqual(writes[0][1], [humanPunch]);
});

test("removing a skill submits the list without it, and a field edit is a patch", async t => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();
    const humanPunch = "EPalWazaID::Human_Punch";
    const kept = "EPalWazaID::FireBall";
    useCatalogsStore().activeSkills = [
        { InternalName: humanPunch, Invalid: false, Assignable: false },
        { InternalName: kept, Invalid: false, Assignable: true },
    ];
    selectPal({
        IsHuman: false,
        EquipWaza: [humanPunch, kept],
        MasteredWaza: [humanPunch, kept],
    });
    const writes = recordSkillWrites(t);
    const patches = [];
    const originalPatch = axios.patch;
    axios.patch = async (url, body) => {
        patches.push([url, body]);
        return { data: operation() };
    };
    t.after(() => { axios.patch = originalPatch; });

    await store.removeMasteredWaza({ target: { name: humanPunch } });
    await store.removeEquipWaza({ target: { name: humanPunch } });
    await store.updatePal({ target: { name: "NickName", value: "ordinary update" } });

    // A removal is the remaining list, not the skill being taken away. There is
    // no generic action name left to pass through: a field the allowlist does not
    // name is now the backend's 400, not something the store decides.
    assert.deepEqual(writes, [
        ["/api/pals/world%3Aselected/skills/mastered", [kept]],
        ["/api/pals/world%3Aselected/skills/equipped", [kept]],
    ]);
    assert.deepEqual(patches, [
        ["/api/pals/world%3Aselected", { NickName: "ordinary update" }],
    ]);
});

