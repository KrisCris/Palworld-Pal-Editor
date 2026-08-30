// Storage resources (spec §8.2, §8.3).
//
// A storage is one place a Pal can be. `listStorages` is the directory the move
// dialog renders; it says what each place is called and how full it is, and
// nothing about whether a particular Pal may go there -- that is
// `getPalTransferCapability`, asked per Pal and per target, because the answer
// depends on the Pal's guild, owner and identity as much as on the target.
//
// Creating a Pal is addressed to the storage it lands in, because the storage is
// what decides the native format it gets written in. Whether the new Pal is a
// default one, a saved template or a record someone pasted in changes only the
// `source`; the target never learns which it was.

import { request } from "./http.js";

const storagePath = storageKey => `/api/storages/${encodeURIComponent(storageKey)}`;

export function listStorages(options) {
    return request("get", "/api/storages", options);
}

// `{allowed, effect, reason, resultRosterKey}`. `effect` is `relocate`,
// `replicate` or `update-existing` and is the backend's word on what this move
// means -- the client shows it and passes it back, it does not re-derive it.
export function getPalTransferCapability(storageKey, sourceRecordKey, options) {
    return request("get", `${storagePath(storageKey)}/pal-transfer-capability`, {
        ...options,
        params: { sourceRecordKey },
    });
}

// Moving a Pal is its own resource because it is a transaction across records the
// client cannot see. `conflictResolution.expectedTarget` is present only after the
// backend has shown the user which existing Pal an overwrite would land on.
export function createPalTransfer(body, options) {
    return request("post", "/api/pal-transfers", { ...options, body });
}

// `source` is `{kind: "default"}`, `{kind: "template", templateId}` or
// `{kind: "native-record", record}`. `ownerUid` is who the new Pal belongs to; the
// Global Palbox and a base camp's container answer that for themselves.
export function createStoragePal(storageKey, source, ownerUid, options) {
    return request("post", `${storagePath(storageKey)}/pals`, {
        ...options,
        body: { source, ownerUid },
    });
}
