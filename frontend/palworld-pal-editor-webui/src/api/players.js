// Player resources.

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

// Restoring a worn item is its own sub-resource, not a field on the PATCH above:
// that call replaces a slot, and a body naming no item empties it. Answers with
// the whole inventory, as the PATCH does.
export function repairInventorySlot(playerUid, slotIndex, containerKind, options) {
    return request(
        "post",
        `${playerPath(playerUid)}/inventory/${slotIndex}/repairs`,
        { ...options, body: { containerKind } },
    );
}
