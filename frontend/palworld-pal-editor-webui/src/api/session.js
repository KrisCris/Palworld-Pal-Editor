// The loaded save, as a resource (spec §8.1).

import { request } from "./http.js";

export function getSession(options) {
    return request("get", "/api/session", options);
}

// `path` may be omitted: the backend then loads whatever it was configured with.
export function putSession(path, options) {
    return request("put", "/api/session", { ...options, body: { path } });
}
