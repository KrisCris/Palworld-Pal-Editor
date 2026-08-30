// Storage resources (spec §8.2, §8.3).
//
// Creating a Pal is addressed to the storage it lands in, because the storage is
// what decides the native format it gets written in. Whether the new Pal is a
// default one, a saved template or a record someone pasted in changes only the
// `source`; the target never learns which it was.
//
// S4a adds `POST /api/pal-transfers` beside this.

import { request } from "./http.js";

// `source` is `{kind: "default"}`, `{kind: "template", templateId}` or
// `{kind: "native-record", record}`. `ownerUid` is who the new Pal belongs to; the
// Global Palbox and a base camp's container answer that for themselves.
export function createStoragePal(storageKey, source, ownerUid, options) {
    return request("post", `/api/storages/${encodeURIComponent(storageKey)}/pals`, {
        ...options,
        body: { source, ownerUid },
    });
}
