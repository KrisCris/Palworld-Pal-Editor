// The Pal lists a save can show (spec §8.2).
//
// A roster answers with `PalSummary[]` in the order that list displays. What a
// single Pal looks like in full is `pals.getPal`, not a bigger roster read.

import { request } from "./http.js";

export function listRosters(options) {
    return request("get", "/api/rosters", options);
}

export function listRosterPals(rosterKey, options) {
    return request(
        "get",
        `/api/rosters/${encodeURIComponent(rosterKey)}/pals`,
        options,
    );
}
