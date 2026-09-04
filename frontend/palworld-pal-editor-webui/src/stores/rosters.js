// The lists of Pals a save can show, and which one is open.
//
// A roster holds `recordKey[]` and nothing else. The Pal behind a key lives in
// `stores/pals`, so a Pal that appears in two lists is still one object and a move
// cannot leave a stale copy behind in the list it came from.

import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";

import { listRosterPals, listRosters } from "../api/rosters.js";
import { readStorage, writeStorage } from "../services/backend-connection.js";
import { usePalsStore } from "./pals.js";
import { useSessionStore } from "./session.js";

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
    const session = useSessionStore();
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
        if (!recordKeysByRoster.value.has(rosterKey)
            && !await loadRosterPals(rosterKey)) return false;
        activeRosterKey.value = rosterKey;
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
        globalPalboxRoster,
        activePlayerUid,
        activeRecordKeys,
        activePals,
        matchesSearch,
        loadRosters,
        loadRosterPals,
        invalidate,
        invalidateAllExcept,
        selectRoster,
        clear,
    };
});
