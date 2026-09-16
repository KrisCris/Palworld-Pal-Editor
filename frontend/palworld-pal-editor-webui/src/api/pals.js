// Pal resources.
//
// `recordKey` is the address of a Pal, not its `InstanceId`: a World copy and a
// Global Palbox copy can carry the same `InstanceId`, so the id alone does not
// say which one is meant.
//
// Every write below answers with the same operation result --
// `{resultRecord, deletedRecordKeys, affectedRosterKeys, affectedStorageKeys}` --
// so a caller never reads back what it just wrote, and never guesses which lists
// an operation disturbed.

import { request } from "./http.js";

const palPath = recordKey => `/api/pals/${encodeURIComponent(recordKey)}`;

export function getPal(recordKey, options) {
    return request("get", palPath(recordKey), options);
}

// The Pal exactly as its own storage format writes it: a World record, or a
// single-entry DPS/Global Palbox array. What comes out here is what
// `POST /api/storages/{key}/pals` accepts back as a `native-record` source.
export function getPalNativeRecord(recordKey, options) {
    return request("get", `${palPath(recordKey)}/native-record`, options);
}

export function deletePal(recordKey, options) {
    return request("delete", palPath(recordKey), options);
}

// No target: the backend picks one, which is what the editor's copy button has
// always done. The reply names the roster the copy landed in.
export function duplicatePal(recordKey, options) {
    return request("post", `${palPath(recordKey)}/duplicates`, options);
}

// Takes only the fields the backend's allowlist names; anything else is a 400.
export function patchPal(recordKey, patch, options) {
    return request("patch", palPath(recordKey), { ...options, body: patch });
}

// `group` is one of `passive`, `equipped`, `mastered`, and `skills` is the list
// the Pal should end up with -- not one skill to add or drop.
export function putPalSkills(recordKey, group, skills, options) {
    return request("put", `${palPath(recordKey)}/skills/${group}`, {
        ...options,
        body: { skills },
    });
}

export function maximizePal(recordKey, options) {
    return request("post", `${palPath(recordKey)}/maximization`, options);
}

// `{scope: "record", recordKey}` or `{scope: "all"}`. One resource, because
// curing an illness and reviving a fainted Pal were always the same operation.
export function healPals(scope, options) {
    return request("post", "/api/pal-heals", { ...options, body: scope });
}
