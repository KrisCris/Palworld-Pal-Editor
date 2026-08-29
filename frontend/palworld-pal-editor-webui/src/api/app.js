// The app itself, rather than the save it has open (spec §8.6).
//
// Three unrelated small things share this client for the same reason they share
// one blueprint on the other side: what the client should boot with, where the
// user can browse for a save, and whether a newer build exists.

import { request } from "./http.js";

// The one call that goes out before there is a token: it is how the client learns
// whether it needs one.
export function getAppConfig(options) {
    return request("get", "/api/app-config", options);
}

// Takes only `i18n` and `donationPromptDismissed`; anything else is a 400.
export function patchAppConfig(patch, options) {
    return request("patch", "/api/app-config", { ...options, body: patch });
}

// A read, and only a read. The server keeps no cursor, so "up one level" is the
// client asking for the `parentPath` it was handed. Omitting `path` opens
// wherever the backend thinks saves live.
export function browseSavePaths(path, options) {
    return request("get", "/api/save-paths", {
        ...options,
        params: path ? { path } : undefined,
    });
}

export function getLatestRelease(options) {
    return request("get", "/api/releases/latest", options);
}
