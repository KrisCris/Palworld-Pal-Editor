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

import { getPal } from "../api/pals.js";
import { useSessionStore } from "./session.js";

export const usePalsStore = defineStore("pals", () => {
    const session = useSessionStore();

    const palsByRecordKey = ref(new Map());
    const selectedRecordKey = ref(null);
    // `changeState` is the backend's answer for `created`; it cannot yet say
    // `modified`, because no route registers one until S2a. Until it can, an edit
    // that succeeded is remembered here, which is what the Pal list's edited
    // marker and filter have always read.
    const editedRecordKeys = ref(new Set());

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

    function markEdited(recordKey) {
        if (recordKey) editedRecordKeys.value.add(recordKey);
    }

    // Every Pal whose detail has been read and reports base-camp illness. The
    // heal-all button has always asked only about Pals already loaded; `S2a`'s
    // `/api/pal-heals` is where that question gets a real answer.
    const hasSickPal = computed(() => [...palsByRecordKey.value.values()].some(
        item => item.detail?.HasWorkerSick,
    ));

    function clear() {
        palsByRecordKey.value = new Map();
        selectedRecordKey.value = null;
        editedRecordKeys.value = new Set();
    }

    return {
        palsByRecordKey,
        selectedRecordKey,
        editedRecordKeys,
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
        markEdited,
        clear,
    };
});
