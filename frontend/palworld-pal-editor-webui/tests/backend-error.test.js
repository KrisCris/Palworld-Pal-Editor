import assert from "node:assert/strict";
import test from "node:test";

import * as paleditor from "../src/stores/paleditor.js";

test("backend failures exclude authentication and ordinary client errors", () => {
    assert.deepEqual(
        paleditor.backendErrorDetails({
            response: {
                status: 500,
                statusText: "Internal Server Error",
                data: {
                    status: 1,
                    msg: "An unexpected error occurred.",
                    data: {
                        error: {
                            code: "AttributeError",
                            log: "Traceback: missing player",
                        },
                    },
                },
            },
        }),
        {
            kind: "application",
            message: "An unexpected error occurred.",
            code: "AttributeError",
            log: "Traceback: missing player",
        }
    );
    assert.deepEqual(
        paleditor.backendErrorDetails({ request: {}, message: "Network Error" }),
        { kind: "connection", message: "Network Error" }
    );
    assert.equal(paleditor.backendErrorDetails({ response: { status: 401 } }), null);
    assert.equal(paleditor.backendErrorDetails({ response: { status: 400 } }), null);
    assert.equal(paleditor.backendErrorDetails(new Error("frontend bug")), null);
});
