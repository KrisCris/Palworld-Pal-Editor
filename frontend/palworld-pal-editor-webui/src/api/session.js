// The loaded save, as a resource (spec §8.1).

import { request } from "./http.js";

export function getSession(options) {
    return request("get", "/api/session", options);
}

// `path` may be omitted: the backend then loads whatever it was configured with.
export function putSession(path, options) {
    return request("put", "/api/session", { ...options, body: { path } });
}

// One save that happened, not a change of session: the answer says where it was
// written, and the session goes on naming the save that is open.
export function postSessionSave(path, options) {
    return request("post", "/api/session/saves", { ...options, body: { path } });
}
