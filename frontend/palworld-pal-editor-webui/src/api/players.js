// Player resources (spec §8.2).

import { request } from "./http.js";

const playerPath = playerUid => `/api/players/${encodeURIComponent(playerUid)}`;

export function listPlayers(options) {
    return request("get", "/api/players", options);
}

// Takes only the fields the backend's allowlist names; anything else is a 400.
// Answers with the whole player, so an edit needs no follow-up read.
export function patchPlayer(playerUid, patch, options) {
    return request("patch", playerPath(playerUid), { ...options, body: patch });
}

export function getPlayerInventory(playerUid, options) {
    return request("get", `${playerPath(playerUid)}/inventory`, options);
}

// `slotIndex` numbers a slot within `containerKind`, which is why the kind is in
// the body. The reply is the whole inventory, not the one slot.
export function patchInventorySlot(playerUid, slotIndex, change, options) {
    return request(
        "patch",
        `${playerPath(playerUid)}/inventory/${slotIndex}`,
        { ...options, body: change },
    );
}
