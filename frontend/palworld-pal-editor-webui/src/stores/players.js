// Players and the inventory of whichever one is open (spec §10).
//
// A player is a plain resource here. The class this replaces carried a `pals` Map
// as well, which made it the fourth place a Pal could live; rosters hold the keys
// now and `stores/pals` holds the Pals.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
    getPlayerInventory,
    listPlayers,
    patchInventorySlot,
    patchPlayer,
} from "../api/players.js";
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

    // Every write below answers with the resource it changed, so none of them
    // follows itself with a read. They return `null` when no player is open,
    // which is the caller's cue to say so -- this store reports nothing.
    async function update(patch) {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) return null;
        const player = await patchPlayer(playerUid, patch);
        playersByUid.value.set(player.InstanceId, player);
        return player;
    }

    async function loadInventory() {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) {
            inventory.value = null;
            return null;
        }
        const epoch = session.sessionEpoch;
        const snapshot = await getPlayerInventory(playerUid, session.readOptions());
        if (!session.isCurrentSession(epoch)) return null;
        inventory.value = snapshot;
        return snapshot;
    }

    async function updateInventorySlot(containerKind, slotIndex, itemId, count, allowOverstack) {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) return null;
        inventory.value = await patchInventorySlot(playerUid, slotIndex, {
            containerKind,
            itemId,
            count,
            allowOverstack,
        });
        return inventory.value;
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
        update,
        loadInventory,
        updateInventorySlot,
        clear,
    };
});
