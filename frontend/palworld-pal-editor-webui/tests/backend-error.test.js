import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "../src/api/http.js";
import * as paleditor from "../src/stores/paleditor.js";

const REQUEST_FAILED = "Backend request failed: An unexpected error occurred.";

test("a backend failure reaches the error screen with its code and traceback", () => {
    const error = new ApiError(500, "AttributeError", "An unexpected error occurred.", {
        traceback: "Traceback: missing player",
    });

    // The code and the traceback are the whole reason this screen has a details
    // block: they are what a user pastes into a bug report.
    assert.deepEqual(paleditor.startupErrorDetails(error, REQUEST_FAILED), {
        kind: "application",
        message: REQUEST_FAILED,
        code: "AttributeError",
        log: "Traceback: missing player",
    });
});

test("a backend that never answered is a connection failure, in its own words", () => {
    const error = new ApiError(0, "CONNECTION_FAILED", "Network Error");

    // Not the translated sentence: the screen shows a different description for
    // this kind, and the fix is choosing another backend rather than retrying.
    assert.deepEqual(paleditor.startupErrorDetails(error, REQUEST_FAILED), {
        kind: "connection",
        message: "Network Error",
    });
});

test("authentication and abandoned requests are not the error screen's business", () => {
    const expired = new ApiError(401, "UNAUTHORIZED", "Token has expired");
    const abandoned = new ApiError(0, "REQUEST_ABORTED", "Request cancelled");

    // An expired token asks for the password again; nobody is waiting on a request
    // whose session was replaced. Neither is a reason to tear the app down.
    assert.equal(paleditor.startupErrorDetails(expired, REQUEST_FAILED), null);
    assert.equal(paleditor.startupErrorDetails(abandoned, REQUEST_FAILED), null);
});

test("an ordinary client error still stops startup, and says which one", () => {
    const error = new ApiError(400, "SAVE_NOT_FOUND", "No save at that path");

    // During startup there is no editor to leave running behind a toast, so a 400
    // goes to the screen like any other failure -- carrying the code that names it.
    assert.deepEqual(paleditor.startupErrorDetails(error, REQUEST_FAILED), {
        kind: "application",
        message: REQUEST_FAILED,
        code: "SAVE_NOT_FOUND",
        log: undefined,
    });
});

test("a request that was never sent reports the frontend stack that explains it", () => {
    const error = new ApiError(0, "FRONTEND_ERROR", "url is not defined");
    error.cause = { stack: "ReferenceError: url is not defined\n    at loadPals" };

    // There is no server traceback for a call that never left the browser, and
    // "request failed" alone is not something anyone can act on.
    assert.deepEqual(paleditor.startupErrorDetails(error, REQUEST_FAILED), {
        kind: "application",
        message: REQUEST_FAILED,
        code: "FRONTEND_ERROR",
        log: "ReferenceError: url is not defined\n    at loadPals",
    });
});
