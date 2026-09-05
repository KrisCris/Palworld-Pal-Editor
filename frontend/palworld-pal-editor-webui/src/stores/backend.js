// Which backend this client is talking to, with what token, and what it means
// when a request to it fails.
//
// Three things that look separate and are not. The origin decides which token
// applies, because a token is remembered per backend; a refused token and a
// backend that never answered are both "you cannot talk to it right now"; and
// both are answered by changing what the app is showing rather than by telling
// the user about a failed operation.
//
// `reportApiFailure` is here, not in `stores/messages`, for that reason: two of
// its four cases are decisions about this connection, and only the last one is a
// message. Every store that makes a request reports through it, which is why it
// sits below them all -- it imports the app, session and messages stores, and
// nothing that makes requests.
//
// What is deliberately not here: choosing a backend and bringing the app up on
// it. That is orchestration across every other store, and it stays in the app
// shell.

import { ref, watch } from "vue";
import { defineStore } from "pinia";

import { setBackendContext } from "../api/http.js";
import {
    backendStorageKey,
    normalizeBackendOrigin,
    readRecentBackends,
    readStorage,
    removeStorage,
    versionedBackendAssetUrl,
    writeStorage,
} from "../services/backend-connection.js";
import { useAppStore } from "./app.js";
import { useMessagesStore } from "./messages.js";
import { useSessionStore } from "./session.js";

export const BACKEND_ORIGIN_KEY = "PAL_BACKEND_ORIGIN";

// What the startup error screen shows for a failed request, or `null` when the
// failure is not the screen's business: nobody is waiting on an abandoned
// request, and an expired token is answered by asking for the password again.
//
// `code` and `log` are the two fields a user can paste into a bug report. They
// reach an `ApiError` as the backend envelope's code and `details.traceback`; a
// request that was never sent has no traceback, and carries the frontend stack
// that explains it instead.
//
// `message` is passed in already translated, because the sentence around the
// backend's own words is interface text and the backend's words are not.
export const startupErrorDetails = (error, message) => {
    if (error?.isAborted || error?.isAuthFailure) return null;
    if (error?.isConnectionFailure) return { kind: "connection", message: error.message };
    return {
        kind: "application",
        message,
        code: error?.code,
        log: error?.details?.traceback || error?.cause?.stack,
    };
};

export const useBackendStore = defineStore("backend", () => {
    const app = useAppStore();
    const session = useSessionStore();
    const messages = useMessagesStore();

    const normalizeStoredBackendOrigin = origin => {
        try { return normalizeBackendOrigin(origin || "", window.location.origin); }
        catch { return ""; }
    };
    // A stored origin written by an older build may not normalize to itself, so
    // it is rewritten now rather than re-normalized on every read.
    const savedBackendOrigin = readStorage(localStorage, BACKEND_ORIGIN_KEY) || "";
    const initialBackendOrigin = normalizeStoredBackendOrigin(savedBackendOrigin);
    if (savedBackendOrigin !== initialBackendOrigin) {
        writeStorage(localStorage, BACKEND_ORIGIN_KEY, initialBackendOrigin);
    }

    // `ORIGIN` is the backend the app belongs to; `CANDIDATE` is the one the user
    // is trying; `REQUEST_ORIGIN` is where calls actually go, which differs from
    // `ORIGIN` for exactly as long as a candidate is being brought up.
    const BACKEND_ORIGIN = ref(initialBackendOrigin);
    const BACKEND_CANDIDATE = ref(BACKEND_ORIGIN.value);
    const BACKEND_REQUEST_ORIGIN = ref(BACKEND_ORIGIN.value);
    const BACKEND_RECENT = ref(readRecentBackends(localStorage));
    const BACKEND_CONNECTED = ref(false);

    const IS_LOCKED = ref(true);
    const BACKEND_ERROR = ref(null);
    const AUTH_MESSAGE_KEY = ref("");

    const backendAssetUrl = path =>
        versionedBackendAssetUrl(BACKEND_ORIGIN.value, path, app.version);
    // Browser storage is keyed per backend, so two backends open in one browser
    // do not share a token or a remembered save path.
    const storageKey = name => backendStorageKey(name, BACKEND_ORIGIN.value);

    // A ref rather than a closure variable because the app shell reads it to
    // decide whether to try `auth()` at all, and puts it back when a candidate
    // backend turns out not to be one.
    const AUTH_TOKEN = ref(readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");

    // The API client holds the token and the origin so no call site has to pass
    // them. They change here, so they are published from here.
    function setAuthToken(token) {
        AUTH_TOKEN.value = token;
        setBackendContext({ token });
    }

    // Whether this browser keeps the token for next time -- only known just after
    // a login, which is the one place that asks.
    function rememberAuthToken(remember) {
        if (remember) writeStorage(localStorage, storageKey("PAL_AUTH_TOKEN"), AUTH_TOKEN.value);
        else removeStorage(localStorage, storageKey("PAL_AUTH_TOKEN"));
    }

    // After the origin changes: the token that applies is a different one.
    function reloadAuthToken() {
        setAuthToken(readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");
    }

    setBackendContext({ origin: BACKEND_REQUEST_ORIGIN.value, token: AUTH_TOKEN.value });
    // Synchronous because `bootstrap` sends its first request in the same tick as
    // it points the app at a new backend; a deferred watcher would publish the
    // origin after that request had already gone to the old one.
    watch(
        BACKEND_REQUEST_ORIGIN,
        origin => setBackendContext({ origin }),
        { flush: "sync" },
    );

    function setBackendError(error) {
        BACKEND_ERROR.value = typeof error === "string"
            ? { kind: "application", message: error }
            : error;
        if (session.appState === "connecting") session.appState = "backend-error";
    }

    function clearBackendError() {
        BACKEND_ERROR.value = null;
    }

    // A backend that never answered is the failure the error screen has its own
    // shape for: the fix is choosing a different backend, not retrying this one.
    function setConnectionError(error) {
        BACKEND_CONNECTED.value = false;
        setBackendError({ kind: "connection", message: error.message });
    }

    function requireAuth(messageKey = "") {
        setAuthToken("");
        rememberAuthToken(false);
        AUTH_MESSAGE_KEY.value = messageKey;
        IS_LOCKED.value = true;
        session.appState = "auth-required";
    }

    // Every REST caller reports failures through here, so a refused token, a
    // backend that cannot be reached and a business error keep behaving the same
    // way without each caller deciding that again.
    function reportApiFailure(error, operationKey) {
        if (error.isAborted) return;
        if (error.isAuthFailure) {
            requireAuth("AuthView_Session_Expired");
            return;
        }
        if (error.isConnectionFailure) {
            setConnectionError(error);
            return;
        }
        // The request was never sent, so this is our bug and is reported with the
        // stack that shows where it is.
        if (error.isFrontendFault) {
            messages.reportFrontendError(
                error.cause ?? error,
                messages.getTranslatedText(operationKey),
            );
            return;
        }
        messages.showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Operation_Failed",
            args: [{ translationKey: operationKey }],
            code: error.code,
            log: error.details?.traceback || error.message,
        });
    }

    // A read that fails while the save is being opened is a failure to start, so
    // it belongs on the backend error screen rather than in a toast over an app
    // that never finished loading.
    function reportStartupFailure(error) {
        const details = startupErrorDetails(
            error,
            messages.getTranslatedText("BackendError_Request_Failed", [error.message]),
        );
        if (!details) {
            if (error.isAuthFailure) requireAuth("AuthView_Session_Expired");
            return;
        }
        if (details.kind === "connection") setConnectionError(error);
        else setBackendError(details);
    }

    return {
        BACKEND_ORIGIN,
        BACKEND_CANDIDATE,
        BACKEND_REQUEST_ORIGIN,
        BACKEND_RECENT,
        BACKEND_CONNECTED,
        BACKEND_ERROR,
        IS_LOCKED,
        AUTH_MESSAGE_KEY,
        AUTH_TOKEN,

        normalizeStoredBackendOrigin,
        backendAssetUrl,
        storageKey,
        setAuthToken,
        rememberAuthToken,
        reloadAuthToken,
        setBackendError,
        clearBackendError,
        setConnectionError,
        requireAuth,
        reportApiFailure,
        reportStartupFailure,
    };
});
