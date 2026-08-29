// Pal resources (spec §8.3).
//
// `recordKey` is the address of a Pal, not its `InstanceId`: a World copy and a
// Global Palbox copy can carry the same `InstanceId`, so the id alone does not
// say which one is meant.

import { request } from "./http.js";

export function getPal(recordKey, options) {
    return request("get", `/api/pals/${encodeURIComponent(recordKey)}`, options);
}
