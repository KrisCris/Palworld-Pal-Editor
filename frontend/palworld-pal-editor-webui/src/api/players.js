// Player resources (spec §8.2).

import { request } from "./http.js";

export function listPlayers(options) {
    return request("get", "/api/players", options);
}

export function getPlayer(playerUid, options) {
    return request("get", `/api/players/${encodeURIComponent(playerUid)}`, options);
}
