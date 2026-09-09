// Players and the inventory of whichever one is open.
//
// A player is a plain resource: it holds no Pals of its own, because a player that
// carried its own `pals` map would be one more place the same Pal could live.
// Rosters hold the keys and `stores/pals` holds the Pals.
//
// Every write here answers with the resource it changed, so none of them follows
// itself with a read. `loadPlayers` is the exception to the reporting below: it
// runs while the save is being opened, and a failure to start is the app shell's
// to describe, so it throws.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
    getPlayerInventory,
    listPlayers,
    patchInventorySlot,
    patchPlayer,
    repairInventorySlot as repairSlotRequest,
} from "../api/players.js";
import { MAX_INVALID_LEVEL, MAX_LEVEL } from "../game-limits.js";
import { useAppStore } from "./app.js";
import { useBackendStore } from "./backend.js";
import { useCatalogsStore } from "./catalogs.js";
import { useMessagesStore } from "./messages.js";
import { usePalsStore } from "./pals.js";
import { useRostersStore } from "./rosters.js";
import { gated, useSessionStore } from "./session.js";

export const usePlayersStore = defineStore("players", () => {
    const app = useAppStore();
    const backend = useBackendStore();
    const catalogs = useCatalogsStore();
    const messages = useMessagesStore();
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

    // The level a control will not go past: the game's ceiling until the user has
    // said they want the wider one.
    const levelCeiling = () => app.HIDE_INVALID_OPTIONS ? MAX_LEVEL : MAX_INVALID_LEVEL;

    async function loadPlayers() {
        const epoch = session.sessionEpoch;
        const rows = await listPlayers(session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        playersByUid.value = new Map(rows.map(row => [row.InstanceId, row]));
        return true;
    }

    // What every field write goes through. Which field names may be written is
    // the backend allowlist's answer, not a method lookup here.
    async function applyPatch(patch) {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) {
            messages.showToast("Message_Select_Player");
            return false;
        }
        try {
            const player = await patchPlayer(playerUid, patch);
            playersByUid.value.set(player.InstanceId, player);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Update_Player");
            return false;
        }
        return true;
    }

    // Called straight from `@click` on the field buttons, whose `name` is the
    // field to write and whose `value` is what to write into it.
    function updateField(e) {
        return applyPatch({ [e.target.name]: e.target.value });
    }

    function levelDown() {
        const player = selectedPlayer.value;
        if (!player || player.Level <= 1) return;
        return applyPatch({ Level: player.Level - 1 });
    }

    function levelUp() {
        const player = selectedPlayer.value;
        if (!player || player.Level >= levelCeiling()) return;
        return applyPatch({ Level: player.Level + 1 });
    }

    function maxLevel() {
        return applyPatch({ Level: levelCeiling() });
    }

    function setStatusPoint(name) {
        const player = selectedPlayer.value;
        if (!player) return;
        let points = Number(player.StatusPointTotals[name]);
        if (!Number.isFinite(points)) points = 0;
        points = Math.min(
            Math.max(Math.trunc(points), player.StatusPointMinimums[name] ?? 0),
            player.StatusPointTotalMaximums[name] ?? 0,
        );
        player.StatusPointTotals[name] = points;
        // A stat point can also be bought with an item, so it is spent against
        // the total; every other kind is the plain allocation.
        const field = player.StatusPointMetadata[name]?.category === "stat"
            ? "StatusPointTotals"
            : "StatusPoints";
        return applyPatch({ [field]: { [name]: points } });
    }

    // The technology field takes the list the player should end up with, so both
    // of these send one: the skill rule, applied to the same shape.
    // Locking compares case-insensitively for the same reason the cards do --
    // the save's spelling of a technology need not be the catalog's, and an
    // exact filter would quietly leave it unlocked.
    function toggleTech(tech, status) {
        const unlocked = selectedPlayer.value?.UnlockedRecipeTechnologyNames ?? [];
        return applyPatch({
            UnlockedRecipeTechnologyNames: status
                ? [...unlocked, tech]
                : unlocked.filter(
                    name => name.toLowerCase() !== tech.toLowerCase(),
                ),
        });
    }

    // The union, not the catalog: this field is a replacement, so sending the
    // catalog alone would lock anything the save has that the catalog does not
    // -- including everything, if the catalog were somehow empty. Unlocking all
    // of them has never been able to take one away, and still cannot.
    function unlockAllTechs() {
        const unlocked = selectedPlayer.value?.UnlockedRecipeTechnologyNames ?? [];
        const everything = Object.values(catalogs.technologiesByLevel)
            .flat()
            .map(tech => tech.InternalName);
        return applyPatch({
            UnlockedRecipeTechnologyNames: [...unlocked, ...everything],
        });
    }

    async function loadInventory() {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) {
            inventory.value = null;
            return false;
        }
        const epoch = session.sessionEpoch;
        let snapshot;
        try {
            snapshot = await getPlayerInventory(playerUid, session.readOptions());
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Load_Player_Data");
            return false;
        }
        if (!session.isCurrentSession(epoch)) return false;
        inventory.value = snapshot;
        return true;
    }

    // Both slot writes answer with the whole inventory, so neither needs a
    // follow-up read.
    async function applySlotWrite(write) {
        const playerUid = rosters.activePlayerUid;
        if (playerUid === null) return false;
        try {
            inventory.value = await write(playerUid);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Update_Player");
            return false;
        }
        return true;
    }

    function updateInventorySlot(containerKind, slotIndex, itemId, count) {
        return applySlotWrite(playerUid => patchInventorySlot(playerUid, slotIndex, {
            containerKind,
            itemId,
            count,
            allowOverstack: !app.HIDE_INVALID_OPTIONS,
        }));
    }

    function repairInventorySlot(containerKind, slotIndex) {
        return applySlotWrite(
            playerUid => repairSlotRequest(playerUid, slotIndex, containerKind),
        );
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
        clear,

        ...gated(session, {
            updateField,
            levelDown,
            levelUp,
            maxLevel,
            setStatusPoint,
            toggleTech,
            unlockAllTechs,
            loadInventory,
            updateInventorySlot,
            repairInventorySlot,
        }),
    };
});
