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

// The storage keys a Pal added to this list may be created in. Where a new Pal may
// go is the save's answer, not a filter over the storage directory: creating one
// into a viewing cage or another guild's base would put it in a list nobody opened.
export function listPalCreationTargets(rosterKey, options) {
    return request(
        "get",
        `/api/rosters/${encodeURIComponent(rosterKey)}/pal-creation-targets`,
        options,
    );
}
