// Players and the inventory of whichever one is open (spec §10).
//
// A player is a plain resource here. The class this replaces carried a `pals` Map
// as well, which made it the fourth place a Pal could live; rosters hold the keys
// now and `stores/pals` holds the Pals.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { getPlayer, listPlayers } from "../api/players.js";
import { usePalsStore } from "./pals.js";
import { useRostersStore } from "./rosters.js";
import { useSessionStore } from "./session.js";

export const usePlayersStore = defineStore("players", () => {
    const session = useSessionStore();
    const rosters = useRostersStore();
    const pals = usePalsStore();

    const playersByUid = ref(new Map());
    const inventory = ref(null);

    const players = computed(() => [...playersByUid.value.values()]);
    const selectedPlayer = computed(() => (
        rosters.activePlayerUid === null
            ? null
            : playersByUid.value.get(rosters.activePlayerUid) ?? null
    ));
    // The player page and the Pal page are the same canvas: a player is being
    // edited exactly when one is open and no Pal of theirs is.
    const showPlayerEditor = computed(() => Boolean(
        selectedPlayer.value && pals.selectedRecordKey === null,
    ));

    async function loadPlayers() {
        const epoch = session.sessionEpoch;
        const rows = await listPlayers(session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        playersByUid.value = new Map(rows.map(row => [row.InstanceId, row]));
        return true;
    }

    async function refreshPlayer(playerUid) {
        const epoch = session.sessionEpoch;
        const player = await getPlayer(playerUid, session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        playersByUid.value.set(player.InstanceId, player);
        return true;
    }

    function clear() {
        playersByUid.value = new Map();
        inventory.value = null;
    }

    return {
        playersByUid,
        inventory,
        players,
        selectedPlayer,
        showPlayerEditor,
        loadPlayers,
        refreshPlayer,
        clear,
    };
});
