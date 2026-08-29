// The one place a Pal lives on the frontend (spec §10).
//
// Before this store there were four: `PAL_MAP` for whatever roster was open,
// `BASE_PAL_MAP`, `GLOBAL_PAL_MAP`, and a `pals` Map inside every `Player`. The
// same Pal appeared in two of them after a move, and which copy the editor showed
// depended on which list you had clicked last. There is now one entry per
// `recordKey` and every list holds keys into it.
//
// An entry is `{summary, detail}`: the summary is what a roster row renders and is
// always there, the detail arrives when the Pal is clicked. Neither ever silently
// replaces the other -- a roster refresh writes its fields through to the detail so
// a Pal that moved does not keep reporting where it used to be, and loading detail
// never drops the summary the list is reading.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
    getPal,
    healPals,
    maximizePal,
    patchPal,
    putPalSkills,
} from "../api/pals.js";
import { useSessionStore } from "./session.js";

export const usePalsStore = defineStore("pals", () => {
    const session = useSessionStore();

    const palsByRecordKey = ref(new Map());
    const selectedRecordKey = ref(null);

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
        if (!palsByRecordKey.value.has(recordKey)) return false;
        if (!await loadDetail(recordKey)) return false;
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

    // Every write answers with the operation result, and the Pal it carries is
    // the new authority for that record -- including its `changeState`, which is
    // how the list's edited marker learns an edit happened.
    function applyOperation(result) {
        if (result.resultRecord) applyDetail(result.resultRecord);
        return result;
    }

    // The five writes below return `null` when no Pal is open. Every editor
    // control is rendered only while one is, so that is a guard, not a message:
    // this store still reports nothing.
    async function update(patch) {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return null;
        return applyOperation(await patchPal(recordKey, patch));
    }

    async function replaceSkills(group, skills) {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return null;
        return applyOperation(await putPalSkills(recordKey, group, skills));
    }

    async function maximize() {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return null;
        return applyOperation(await maximizePal(recordKey));
    }

    async function heal() {
        const recordKey = selectedRecordKey.value;
        if (recordKey === null) return null;
        return applyOperation(await healPals({ scope: "record", recordKey }));
    }

    // The only write with no single record to answer for: it names the rosters
    // whose rows changed instead, and the caller decides what to re-read.
    async function healAll() {
        return applyOperation(await healPals({ scope: "all" }));
    }

    // Every Pal whose detail has been read and reports base-camp illness. The
    // heal-all button has always asked only about Pals already loaded.
    const hasSickPal = computed(() => [...palsByRecordKey.value.values()].some(
        item => item.detail?.HasWorkerSick,
    ));

    function clear() {
        palsByRecordKey.value = new Map();
        selectedRecordKey.value = null;
    }

    return {
        palsByRecordKey,
        selectedRecordKey,
        selectedPal,
        selectedPalLoaded,
        hasSickPal,
        summary,
        upsertSummaries,
        applyDetail,
        loadDetail,
        select,
        clearSelection,
        forget,
        update,
        replaceSkills,
        maximize,
        heal,
        healAll,
        clear,
    };
});
