// One place that knows how to reach the backend.
//
// Every REST call goes through `request()` and either returns the parsed body or
// throws an `ApiError`. That is the whole point of this module: callers do not
// inspect `response.status == 0 / 1 / 2` and guess what to do, which makes every
// new endpoint another three-branch ladder written from memory. A thrown error is
// handled once, at the operation, or not at all.

import axios from "axios";

import { backendUrl } from "../services/backend-connection.js";

// The backend's error envelope, plus the two failures that never reach a route: the request
// was cancelled because its session is gone, or the backend is not there at all.
export class ApiError extends Error {
    constructor(httpStatus, code, message, details = {}) {
        super(message || code);
        this.name = "ApiError";
        this.httpStatus = httpStatus;
        this.code = code;
        this.details = details;
    }

    // The token is missing, expired or refused. Not a business failure: the caller
    // stops what it is doing and asks for the password again.
    get isAuthFailure() {
        return this.httpStatus === 401;
    }

    // Nothing answered. The backend moved, went down, or was never there.
    get isConnectionFailure() {
        return this.code === "CONNECTION_FAILED";
    }

    // The session this request belonged to was replaced while it was in flight.
    // Nobody is waiting for the answer, so nothing is reported.
    get isAborted() {
        return this.code === "REQUEST_ABORTED";
    }

    // The request never got as far as being sent. That is a fault in this code,
    // not in the backend, and it is reported as one -- with the stack, because
    // nobody can act on "connection failed" when the connection was never tried.
    get isFrontendFault() {
        return this.code === "FRONTEND_ERROR";
    }
}

// The backend this app is talking to and the token it is talking with. They live
// here rather than being passed to every call because there is exactly one of
// each at a time; the store owns when they change and says so through
// `setBackendContext`.
let backendOrigin = "";
let authToken = "";

export function setBackendContext({ origin, token } = {}) {
    if (origin !== undefined) backendOrigin = origin;
    if (token !== undefined) authToken = token;
}

export function apiUrl(path) {
    return backendUrl(backendOrigin, path);
}

function toApiError(error) {
    if (error?.code === "ERR_CANCELED" || error?.name === "CanceledError") {
        return new ApiError(0, "REQUEST_ABORTED", "Request cancelled");
    }

    const response = error?.response;
    if (!response) {
        // axios attaches `request` once it has something in flight; without it
        // the failure happened while building the call.
        const code = error?.request ? "CONNECTION_FAILED" : "FRONTEND_ERROR";
        const failure = new ApiError(0, code, error?.message || "Network Error");
        failure.cause = error;
        return failure;
    }

    const envelope = response.data?.error;
    if (envelope?.code) {
        return new ApiError(
            response.status,
            envelope.code,
            envelope.message || "",
            envelope.details || {},
        );
    }

    // Not a REST blueprint: the JWT handlers answer `{status, data, msg}`. 401 is
    // the case that matters, and it comes from the app-level auth handlers rather
    // than from a route.
    const status = response.status;
    return new ApiError(
        status,
        status === 401 ? "UNAUTHORIZED" : "UNEXPECTED_ERROR",
        response.data?.msg || `${response.statusText || "HTTP"}: ${status}`,
        response.data?.data?.error ?? {},
    );
}

// axios splits its methods by whether they carry a body, so this does too rather
// than routing everything through `axios.request`.
const SENDS_BODY = new Set(["post", "put", "patch"]);

export async function request(method, path, { body, params, signal } = {}) {
    const url = apiUrl(path);
    const config = {
        params,
        signal,
        headers: { Authorization: `Bearer ${authToken}` },
    };
    try {
        const response = SENDS_BODY.has(method)
            ? await axios[method](url, body, config)
            : await axios[method](url, config);
        return response.data;
    } catch (error) {
        throw toApiError(error);
    }
}
