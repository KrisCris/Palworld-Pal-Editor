// The one place a Pal lives on the frontend, and everything that edits one.
//
// One entry per `recordKey`, with every list holding keys into it. Splitting Pals
// across per-roster maps instead lets the same Pal sit in two of them after a
// move, and then which copy the editor shows depends on which list was clicked
// last.
//
// An entry is `{summary, detail}`: the summary is what a roster row renders and is
// always there, the detail arrives when the Pal is clicked. Neither ever silently
// replaces the other -- a roster refresh writes its fields through to the detail so
// a Pal that moved does not keep reporting where it used to be, and loading detail
// never drops the summary the list is reading.
//
// What is deliberately not here: creating, deleting and moving a Pal. Each of
// those changes which list the Pal is in and which list is on screen, so all
// three live together in `stores/rosters` with the rest of that question.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
    deletePal,
    duplicatePal,
    getPal,
    getPalNativeRecord,
    healPals,
    maximizePal,
    patchPal,
    putPalSkills,
} from "../api/pals.js";
import { createStoragePal } from "../api/storages.js";
import { applySkillTemplate } from "../api/templates.js";
import {
    MAX_EQUIP_WAZA,
    MAX_FRIENDSHIP_LEVEL,
    MAX_INVALID_LEVEL,
    MAX_LEVEL,
    MAX_SUITABILITY_LEVEL,
} from "../game-limits.js";
import { maximumSuitabilities } from "../pal-traits.js";
import { isSkillAssignable } from "../skill-rules.js";
import { useAppStore } from "./app.js";
import { useBackendStore } from "./backend.js";
import { useCatalogsStore } from "./catalogs.js";
import { useMessagesStore } from "./messages.js";
import { applyOperationResult } from "./operation-result.js";
import { gated, useSessionStore } from "./session.js";

export const usePalsStore = defineStore("pals", () => {
    const app = useAppStore();
    const backend = useBackendStore();
    const catalogs = useCatalogsStore();
    const messages = useMessagesStore();
    const session = useSessionStore();

    const palsByRecordKey = ref(new Map());
    const selectedRecordKey = ref(null);

    // The two skill pickers' current choice, which is a control's state and not
    // the Pal's: it becomes the Pal's only when the add button is pressed.
    const passiveSkillChoice = ref("");
    const activeSkillChoice = ref("");
    // Bumped by every write that landed on the open Pal, so the list can scroll
    // the row back into view. The Pal itself is already updated in place.
    const writeCount = ref(0);
    // Whether the editor's save-details disclosure is open, kept here so it
    // survives the panel being remounted for another Pal.
    const saveDetailsOpen = ref(false);

    const entry = recordKey => palsByRecordKey.value.get(recordKey) ?? null;
    const summary = recordKey => entry(recordKey)?.summary ?? null;

    const selectedEntry = computed(() => entry(selectedRecordKey.value));
    // The stored object itself, not a merge of the two halves: the editor binds
    // `v-model` straight to its fields, and only an object that lives inside the
    // cache re-renders when one of those bindings writes to it.
    const selectedPal = computed(() => (
        selectedEntry.value?.detail ?? selectedEntry.value?.summary ?? null
    ));
    // Whether the editor panel has everything it renders. A Pal that is selected
    // but not yet fetched is a list row, not an editor page.
    const selectedPalLoaded = computed(() => Boolean(selectedEntry.value?.detail));

    function upsertSummary(row) {
        const current = entry(row.recordKey);
        palsByRecordKey.value.set(row.recordKey, {
            summary: row,
            // A move changes the fields the summary and the detail share. The
            // detail is the one the editor reads, so it takes the new values too.
            detail: current?.detail ? { ...current.detail, ...row } : null,
        });
    }

    function upsertSummaries(rows) {
        for (const row of rows) upsertSummary(row);
    }

    function applyDetail(detail) {
        const current = entry(detail.recordKey);
        palsByRecordKey.value.set(detail.recordKey, {
            // Detail is a strict superset of summary and agrees with it field for
            // field, so it refreshes the list row it was fetched from.
            summary: { ...(current?.summary ?? {}), ...detail },
            detail,
        });
    }

    // A successful save makes every "new" and "edited" marker stale at
    // once, and the backend has already forgotten them. Only that one field is
    // rewritten -- the cached objects stay as they are, because the editor is
    // holding the selected detail and binds `v-model` straight into it.
    function clearChangeStates() {
        for (const { summary, detail } of palsByRecordKey.value.values()) {
            if (summary) summary.changeState = "unchanged";
            if (detail) detail.changeState = "unchanged";
        }
    }

    // Throws, unlike everything below it: the app shell reads a Pal again while
    // bringing a save up or after a language change, and a failure there is a
    // failure to start rather than a failed operation.
    async function loadDetail(recordKey) {
        const epoch = session.sessionEpoch;
        const detail = await getPal(recordKey, session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        applyDetail(detail);
        return true;
    }

    // Selection moves only once the payload is in: a half-loaded Pal on screen is
    // worse than the previous one staying a moment longer.
    async function select(recordKey) {
        if (!palsByRecordKey.value.has(recordKey)) {
            messages.showToast("Message_Select_Pal_Failed");
            return false;
        }
        try {
            if (!await loadDetail(recordKey)) return false;
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Load_Pal");
            return false;
        }
        selectedRecordKey.value = recordKey;
        return true;
    }

    function clearSelection() {
        selectedRecordKey.value = null;
    }

    function forget(recordKey) {
        palsByRecordKey.value.delete(recordKey);
        if (selectedRecordKey.value === recordKey) selectedRecordKey.value = null;
    }

    // The Pal on screen took a new address. Not a selection: it is already in the
    // cache under the new key, so nothing is read and nothing is shown that was
    // not being shown a moment ago.
    function reselect(recordKey) {
        selectedRecordKey.value = recordKey;
    }

    // ---- writes --------------------------------------------------------------
    // Every write answers with the Pal it changed, so none of them re-reads it
    // afterwards. All of them run only while a Pal is open, which the editor
    // controls guarantee by existing -- so no Pal open is a guard, not a message.

    async function runWrite(write, operationKey = "Operation_Update_Pal") {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return false;
        try {
            await applyOperationResult(await write(recordKey));
        } catch (error) {
            backend.reportApiFailure(error, operationKey);
            return false;
        }
        writeCount.value++;
        return true;
    }

    const applyPatch = patch => runWrite(recordKey => patchPal(recordKey, patch));

    // A skill group is submitted whole. The callers build the list the Pal should
    // end up with; the backend refuses one the game cannot resolve.
    //
    // The repeat is dropped here rather than in each caller because it is not the
    // caller that puts it there: a save can already hold the same passive twice,
    // and appending to that list is a request the backend refuses whichever skill
    // was chosen -- so the Pal could never be edited out of the state it arrived
    // in. A list the Pal should end up with never names a skill twice.
    const replaceSkills = (group, skills) => runWrite(
        recordKey => putPalSkills(recordKey, group, [...new Set(skills)]),
    );

    // Called straight from `@click`/`@change`, whose `name` is the field to write
    // and whose `value` is what to write into it. Whether that name may be
    // written is the backend allowlist's answer, not a method lookup.
    function updateField(e) {
        return applyPatch({ [e.target.name]: e.target.value });
    }

    const editedPal = () => selectedPal.value;
    const levelCeiling = () => app.HIDE_INVALID_OPTIONS ? MAX_LEVEL : MAX_INVALID_LEVEL;

    function swapRare() {
        return applyPatch({ IsRarePal: !editedPal().IsRarePal });
    }

    function swapBoss() {
        return applyPatch({ IsBOSS: !editedPal().IsBOSS });
    }

    function toggleAwakening() {
        return applyPatch({ IsAwakening: !editedPal().IsAwakening });
    }

    function levelDown() {
        const pal = editedPal();
        if (pal.Level <= 1) return;
        return applyPatch({ Level: pal.Level - 1 });
    }

    function levelUp() {
        const pal = editedPal();
        if (pal.Level >= levelCeiling()) return;
        return applyPatch({ Level: pal.Level + 1 });
    }

    function maxLevel() {
        return applyPatch({ Level: levelCeiling() });
    }

    function friendshipDown() {
        const pal = editedPal();
        if (pal.FriendshipLevel <= -3) return;
        return applyPatch({ FriendshipLevel: pal.FriendshipLevel - 1 });
    }

    function friendshipUp() {
        const pal = editedPal();
        if (pal.FriendshipLevel >= MAX_FRIENDSHIP_LEVEL) return;
        return applyPatch({ FriendshipLevel: pal.FriendshipLevel + 1 });
    }

    function maxFriendship() {
        return applyPatch({ FriendshipLevel: MAX_FRIENDSHIP_LEVEL });
    }

    function swapGender() {
        const gender = editedPal().Gender;
        let next = app.HIDE_INVALID_OPTIONS ? "NONE" : "EPalGenderType::Female";
        if (gender == "EPalGenderType::Female") next = "EPalGenderType::Male";
        if (gender == "EPalGenderType::Male") next = "EPalGenderType::Female";
        return applyPatch({ Gender: next });
    }

    function changeSpecies(characterId) {
        return applyPatch({ CharacterID: characterId });
    }

    // A skill the game has no entry for is one the backend would refuse, and one
    // the UI cannot draw either -- so the dropdown selections are checked here
    // before a request is worth making. The `Invalid`/human rules are the same
    // check the skill picker already greys the option out with.
    function assignableActiveSkill(skill) {
        const active = catalogs.activeSkillsByName[skill];
        if (!active) return false;
        return !app.HIDE_INVALID_OPTIONS
            || isSkillAssignable(active, selectedPal.value?.IsHuman);
    }

    function removePassiveSkill(e) {
        return replaceSkills(
            "passive",
            editedPal().PassiveSkillList.filter(skill => skill !== e.target.name),
        );
    }

    function addPassiveSkill() {
        const skill = passiveSkillChoice.value;
        if (!catalogs.passiveSkillsByName[skill]) {
            messages.showToast("Message_Select_Skill");
            return;
        }
        if (app.HIDE_INVALID_OPTIONS && editedPal().PassiveSkillList.length >= 4) {
            messages.showToast("Message_Passive_Limit");
            return;
        }
        return replaceSkills("passive", [...editedPal().PassiveSkillList, skill]);
    }

    function removeEquipWaza(e) {
        return replaceSkills(
            "equipped",
            editedPal().EquipWaza.filter(waza => waza !== e.target.name),
        );
    }

    function addEquipWaza(e) {
        if (!assignableActiveSkill(e.target.name)) {
            messages.showToast("Message_Skill_Not_Assignable");
            return;
        }
        // Equipping a move also learns it, so this one list says both.
        return replaceSkills("equipped", [...editedPal().EquipWaza, e.target.name]);
    }

    function removeMasteredWaza(e) {
        return replaceSkills(
            "mastered",
            editedPal().MasteredWaza.filter(waza => waza !== e.target.name),
        );
    }

    function addMasteredWaza() {
        const skill = activeSkillChoice.value;
        if (!catalogs.activeSkillsByName[skill]) {
            messages.showToast("Message_Select_Skill");
            return;
        }
        if (!assignableActiveSkill(skill)) {
            messages.showToast("Message_Skill_Not_Assignable");
            return;
        }
        const pal = editedPal();
        // Learning a move with an active slot free has always equipped it too,
        // and equipping is what learns it -- so the equipped list carries both.
        if (pal.EquipWaza.length < MAX_EQUIP_WAZA) {
            return replaceSkills("equipped", [...pal.EquipWaza, skill]);
        }
        return replaceSkills("mastered", [...pal.MasteredWaza, skill]);
    }

    function setSuitability(name, value) {
        const pal = editedPal();
        const min = pal.SuitabilityMinimums[name] || 0;
        if (app.HIDE_INVALID_OPTIONS && min == 0 && value != 0) {
            messages.showToast("Message_Invalid_Suitability");
            return;
        }
        value = Math.min(Math.max(value, min), MAX_SUITABILITY_LEVEL);
        if (value == pal.Suitabilities[name]) return;
        return applyPatch({ Suitabilities: { [name]: value } });
    }

    function suitabilityUp(e) {
        const name = e.target.name;
        return setSuitability(name, editedPal().Suitabilities[name] + 1);
    }

    function suitabilityDown(e) {
        const name = e.target.name;
        return setSuitability(name, editedPal().Suitabilities[name] - 1);
    }

    function maxSuitabilities() {
        const values = maximumSuitabilities(
            editedPal().SuitabilityMinimums,
            MAX_SUITABILITY_LEVEL,
        );
        if (!Object.keys(values).length) return;
        return applyPatch({ Suitabilities: values });
    }

    // The three buttons the editor and the top bar show are one operation: curing
    // an illness and reviving a fainted Pal already ran the same code.
    function heal() {
        return runWrite(recordKey => healPals({ scope: "record", recordKey }));
    }

    // The one write with no single record to answer for: it names the rosters
    // whose rows changed instead, so nothing in the reply can say what the heal
    // did to the Pal on screen and that one is re-read.
    async function healAll() {
        try {
            await applyOperationResult(await healPals({ scope: "all" }));
            if (selectedRecordKey.value) await loadDetail(selectedRecordKey.value);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Update_Pal");
            return false;
        }
        return true;
    }

    async function maximize() {
        if (!await runWrite(maximizePal, "Operation_Maximize_Pal")) return false;
        messages.showToast("Message_Pal_Maximized", "success");
        return true;
    }

    // Applying a skill template is a Pal write, not a template read: it answers
    // with the Pal it changed, so nothing is re-read afterwards.
    async function applyTemplate(templateId) {
        if (!await runWrite(
            recordKey => applySkillTemplate(recordKey, templateId),
            "Operation_Apply_Skill_Template",
        )) return false;
        messages.showToast("Message_Skill_Template_Applied", "success");
        return true;
    }

    // The export button copies the Pal as its own storage writes it, formatted
    // here rather than by the backend: what crosses the wire is the record, and
    // indentation is a property of what lands on the clipboard. Nothing is
    // cached -- it is a whole save record and only this ever wants one.
    async function copyNativeRecord() {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return false;
        let record;
        try {
            record = await getPalNativeRecord(recordKey);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Copy_Pal");
            return false;
        }
        try {
            await navigator.clipboard.writeText(JSON.stringify(record, null, 4));
        } catch (error) {
            // Refusing the clipboard is the browser's to do, and it is the only
            // half of this that was never a request.
            messages.reportFrontendError(
                error,
                app.getTranslatedText("Operation_Copy_Pal"),
            );
            return false;
        }
        messages.showToast("Message_Pal_Copied", "success");
        return true;
    }

    // Creating, copying and deleting all answer with the same result, so none of
    // them tells this store where the Pal went -- `applyOperationResult` reads
    // that off the reply. They throw, because the list that has to be opened
    // afterwards is `stores/rosters`' business and so is saying what failed.
    async function create(storageKey, source, ownerUid) {
        return applyOperationResult(
            await createStoragePal(storageKey, source, ownerUid),
        );
    }

    async function duplicate(recordKey) {
        return applyOperationResult(await duplicatePal(recordKey));
    }

    // The copy lands beside the original, in the same list, so this one needs no
    // help from the roster store: the new Pal is simply opened.
    async function duplicateSelected() {
        let result;
        try {
            result = await duplicate(selectedRecordKey.value);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Duplicate_Pal");
            return false;
        }
        return select(result.resultRecord.recordKey);
    }

    async function remove(recordKey) {
        return applyOperationResult(await deletePal(recordKey));
    }

    // Every Pal whose detail has been read and reports base-camp illness. The
    // heal-all button has always asked only about Pals already loaded.
    const hasSickPal = computed(() => [...palsByRecordKey.value.values()].some(
        item => item.detail?.HasWorkerSick,
    ));

    function clear() {
        palsByRecordKey.value = new Map();
        selectedRecordKey.value = null;
        passiveSkillChoice.value = "";
        activeSkillChoice.value = "";
    }

    return {
        palsByRecordKey,
        selectedRecordKey,
        selectedPal,
        selectedPalLoaded,
        hasSickPal,
        passiveSkillChoice,
        activeSkillChoice,
        writeCount,
        saveDetailsOpen,

        summary,
        upsertSummaries,
        applyDetail,
        clearChangeStates,
        loadDetail,
        clearSelection,
        forget,
        reselect,
        create,
        duplicate,
        remove,
        clear,

        ...gated(session, {
            select,
            updateField,
            swapRare,
            swapBoss,
            toggleAwakening,
            levelDown,
            levelUp,
            maxLevel,
            friendshipDown,
            friendshipUp,
            maxFriendship,
            swapGender,
            changeSpecies,
            removePassiveSkill,
            addPassiveSkill,
            removeEquipWaza,
            addEquipWaza,
            removeMasteredWaza,
            addMasteredWaza,
            suitabilityUp,
            suitabilityDown,
            maxSuitabilities,
            heal,
            healAll,
            maximize,
            applyTemplate,
            copyNativeRecord,
            duplicateSelected,
        }),
    };
});
