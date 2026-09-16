// The lists of Pals a save can show, which one is open, and everything that
// changes which list a Pal is in.
//
// A roster holds `recordKey[]` and nothing else. The Pal behind a key lives in
// `stores/pals`, so a Pal that appears in two lists is still one object and a move
// cannot leave a stale copy behind in the list it came from.
//
// Creating, deleting and moving a Pal live here, together, because all three end
// the same way: the reply names the list the Pal is now in, that list is opened,
// and the Pal is shown in it. Splitting them between the store that holds the Pal
// and the one that holds the storages would write that ending twice, in two
// stores that would then each need the other.

import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";

import { listRosterPals, listRosters } from "../api/rosters.js";
import { readStorage, writeStorage } from "../services/backend-connection.js";
import { useBackendStore } from "./backend.js";
import { useMessagesStore } from "./messages.js";
import { usePalsStore } from "./pals.js";
import { useResearchStore } from "./research.js";
import { gated, useSessionStore } from "./session.js";
import { useStoragesStore } from "./storages.js";

export const BASE_ROSTER_KEY = "base-workers";
export const GLOBAL_PALBOX_ROSTER_KEY = "global-palbox";
export const PLAYER_ROSTER_PREFIX = "player:";

export const playerRosterKey = playerUid => `${PLAYER_ROSTER_PREFIX}${playerUid}`;

const PAL_LIST_PREFERENCES_KEY = "PAL_LIST_PREFERENCES";
const PAL_LIST_SORT_VALUES = new Set(["paldeck", "location", "priority"]);
const PAL_LIST_ATTRIBUTE_VALUES = new Set([
    "priority-1", "priority-2", "priority-3", "alpha", "lucky", "dna", "human",
]);

function savedListPreferences() {
    try {
        return JSON.parse(readStorage(localStorage, PAL_LIST_PREFERENCES_KEY) || "{}");
    } catch {
        return {};
    }
}

export const useRostersStore = defineStore("rosters", () => {
    const backend = useBackendStore();
    const messages = useMessagesStore();
    const research = useResearchStore();
    const session = useSessionStore();
    const storages = useStoragesStore();
    const pals = usePalsStore();

    const rosters = ref([]);
    const activeRosterKey = ref(null);
    const recordKeysByRoster = ref(new Map());

    const preferences = savedListPreferences();
    const searchKeyword = ref("");
    const sortMode = ref(PAL_LIST_SORT_VALUES.has(preferences.sort)
        ? preferences.sort : "paldeck");
    const attributeFilters = ref(Array.isArray(preferences.attributes)
        ? [...new Set(preferences.attributes.filter(
            value => PAL_LIST_ATTRIBUTE_VALUES.has(value),
        ))]
        : []);
    const editedOnly = ref(false);
    const createdOnly = ref(false);
    watch([sortMode, attributeFilters], ([sort, attributes]) => {
        writeStorage(localStorage, PAL_LIST_PREFERENCES_KEY, JSON.stringify({
            sort, attributes,
        }));
    }, { deep: true });

    const hasBaseRoster = computed(() => rosters.value.some(
        roster => roster.kind === "base",
    ));
    // A base camp is worth listing even when nobody works in it yet, so the base
    // camp button follows the storages as well as this listing.
    const hasBaseCamp = computed(
        () => hasBaseRoster.value || storages.hasBaseStorage,
    );
    const globalPalboxRoster = computed(() => rosters.value.find(
        roster => roster.kind === "global_palbox",
    ) ?? null);
    // A roster key is either a player's or one of the fixed places, so the player
    // the editor is showing is a fact about the roster and not a second selection.
    const activePlayerUid = computed(() => (
        activeRosterKey.value?.startsWith(PLAYER_ROSTER_PREFIX)
            ? activeRosterKey.value.slice(PLAYER_ROSTER_PREFIX.length)
            : null
    ));
    const activeRecordKeys = computed(() => (
        recordKeysByRoster.value.get(activeRosterKey.value) ?? []
    ));
    const activePals = computed(() => activeRecordKeys.value
        .map(recordKey => pals.summary(recordKey))
        .filter(Boolean));

    const matchesSearch = pal => !searchKeyword.value
        || String(pal?.DisplayName ?? "").toLowerCase()
            .includes(searchKeyword.value.toLowerCase());

    // Throws, like the other reads the app shell runs while a save is opening: a
    // failure there is a failure to start, and the shell is what says so.
    async function loadRosters() {
        const epoch = session.sessionEpoch;
        const entries = await listRosters(session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        rosters.value = entries;
        return true;
    }

    async function loadRosterPals(rosterKey) {
        const epoch = session.sessionEpoch;
        const rows = await listRosterPals(rosterKey, session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        pals.upsertSummaries(rows);
        recordKeysByRoster.value.set(rosterKey, rows.map(row => row.recordKey));
        return true;
    }

    // Only rosters that have been read are cached, so dropping one is how a list
    // is re-read in a new language or after an operation moved Pals through it.
    function invalidate(rosterKey) {
        recordKeysByRoster.value.delete(rosterKey);
    }

    function invalidateAllExcept(rosterKey) {
        for (const key of [...recordKeysByRoster.value.keys()]) {
            if (key !== rosterKey) recordKeysByRoster.value.delete(key);
        }
    }

    async function selectRoster(rosterKey) {
        pals.clearSelection();
        activeRosterKey.value = null;
        try {
            if (!recordKeysByRoster.value.has(rosterKey)
                && !await loadRosterPals(rosterKey)) return false;
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Load_Pals");
            return false;
        }
        activeRosterKey.value = rosterKey;
        // The base camp is the only list with a laboratory behind it.
        if (rosterKey === BASE_ROSTER_KEY) await research.load();
        return true;
    }

    // ---- creating, deleting and moving a Pal ---------------------------------

    // The row the list would land on once the current one is gone: the next Pal
    // the filters still show, or the first if there is none after it.
    function nextVisibleRecordKey(recordKey) {
        const visible = activeRecordKeys.value.filter(
            key => matchesSearch(pals.summary(key)),
        );
        const index = visible.indexOf(recordKey);
        return visible.find((key, position) => position > index && key !== recordKey)
            ?? visible.find(key => key !== recordKey)
            ?? null;
    }

    async function deletePal() {
        const recordKey = pals.selectedRecordKey;
        const successor = nextVisibleRecordKey(recordKey);
        try {
            await pals.remove(recordKey);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Delete_Pal");
            return false;
        }
        if (successor && pals.summary(successor)) await pals.select(successor);
        return true;
    }

    // Every transfer ends the same way: the lists the reply named are already
    // refreshed, so what is left is opening the list the Pal is now in and
    // showing it there.
    async function followTransfer(result, rosterKey) {
        if (rosterKey !== activeRosterKey.value && !await selectRoster(rosterKey)) {
            return false;
        }
        return pals.select(result.resultRecord.recordKey);
    }

    async function movePal(targetStorageKey) {
        // Read before the move: this is the answer the user was shown, and it
        // names the list the Pal is about to be in.
        const capability = storages.capability(targetStorageKey);
        let result;
        try {
            result = await storages.movePal(targetStorageKey);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
        // The backend answered with a question rather than a result: the dialog
        // is now showing which existing Pal an overwrite would land on.
        if (result === null) return false;
        await followTransfer(result, capability.resultRosterKey);
        messages.showToast("Message_Pal_Moved", "success");
        return true;
    }

    async function overwriteConflictingPal() {
        if (!storages.conflictTarget) return false;
        const capability = storages.capability(storages.conflict.targetStorageKey);
        let result;
        try {
            result = await storages.overwriteConflictTarget();
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
        if (result === null) return false;
        await followTransfer(result, capability.resultRosterKey);
        messages.showToast("Message_Pal_Updated", "success");
        return true;
    }

    // Go and look at the Pal that is in the way instead of overwriting it. For an
    // overwrite the capability's result roster is the destination's, which is
    // exactly the list that Pal is sitting in.
    async function jumpToConflictingPal() {
        const target = storages.conflictTarget;
        if (!target) return false;
        const { resultRosterKey } = storages.capability(
            storages.conflict.targetStorageKey,
        );
        storages.clearConflict();
        if (resultRosterKey !== activeRosterKey.value
            && !await selectRoster(resultRosterKey)) return false;
        return pals.select(target.recordKey);
    }

    // Which storages the add dialog may offer, for the list that is open. The
    // answer is the save's, so a target that would put the new Pal in a list
    // nobody opened is never on screen.
    async function loadCreationTargets() {
        try {
            return await storages.creationTargets(activeRosterKey.value);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Add_Pal");
            return [];
        }
    }

    // The add dialog's three tabs are one operation with three sources: a default
    // Pal, a saved template, or a record pasted in as JSON. Where it lands and who
    // owns it are the same question whichever tab is open, so only `source`
    // differs and the target storage builds the native record.
    async function addPal({
        mode = "default", templateId, palJson, targetStorageKey,
    } = {}) {
        let source;
        if (mode === "template") {
            source = { kind: "template", templateId };
        } else if (mode === "json") {
            try {
                source = { kind: "native-record", record: JSON.parse(palJson) };
            } catch (error) {
                // Text that is not JSON never reaches the backend, so there is no
                // reply for it to fail with; this says so in the dialog the same
                // way a refused record would.
                messages.showMessage({
                    severity: "error",
                    presentation: "dialog",
                    messageKey: "Message_Operation_Failed",
                    args: [{ translationKey: "Operation_Add_Pal" }],
                    code: "PAL_JSON_INVALID",
                    log: error.message,
                });
                return false;
            }
        } else {
            source = { kind: "default" };
        }

        let result;
        try {
            result = await pals.create(
                targetStorageKey, source, activePlayerUid.value,
            );
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Add_Pal");
            return false;
        }
        // Which list the new Pal turned up in is the reply's answer, not a guess
        // from the target container's kind and owner.
        const [targetRoster] = result.affectedRosterKeys;
        if (targetRoster && targetRoster !== activeRosterKey.value) {
            await selectRoster(targetRoster);
        }
        await pals.select(result.resultRecord.recordKey);
        return true;
    }

    function clear() {
        rosters.value = [];
        activeRosterKey.value = null;
        recordKeysByRoster.value = new Map();
        searchKeyword.value = "";
        editedOnly.value = false;
        createdOnly.value = false;
    }

    return {
        rosters,
        activeRosterKey,
        recordKeysByRoster,
        searchKeyword,
        sortMode,
        attributeFilters,
        editedOnly,
        createdOnly,
        hasBaseRoster,
        hasBaseCamp,
        globalPalboxRoster,
        activePlayerUid,
        activeRecordKeys,
        activePals,
        matchesSearch,
        loadRosters,
        loadRosterPals,
        invalidate,
        invalidateAllExcept,
        clear,

        ...gated(session, {
            selectRoster,
            deletePal,
            addPal,
            movePal,
            overwriteConflictingPal,
            jumpToConflictingPal,
            loadCreationTargets,
        }),
    };
});
