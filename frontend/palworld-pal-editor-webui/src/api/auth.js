// The two calls that decide whether this client may talk to the backend at all.
//
// These are the last endpoints that still answer `{status, data, msg}` rather than
// the REST error envelope, because they are served by the app-level JWT handlers
// and not by a blueprint. `toApiError` already turns a 401 from them into an
// `ApiError` with code `UNAUTHORIZED`, so a caller here handles a refused password
// the same way it handles any other failure: by catching.
//
// What stays in the body is the part no HTTP status carries -- `status === 0` for
// a token that is good, and the token itself on a successful login.

import { request } from "./http.js";

// Whether the token this client is holding is still accepted. Answers a body, not
// a boolean: an expired token comes back as a 401 and therefore as a thrown
// `ApiError`, which is the caller's cue to ask for the password again.
export function checkAuth(options) {
    return request("get", "/api/auth/auth", options);
}

// `remember` asks the backend for a token with no expiry. Where that token is then
// kept is the store's business, not this module's.
export function login(password, remember = false, options) {
    return request("post", "/api/auth/login", {
        ...options,
        body: { password, remember },
    });
}
