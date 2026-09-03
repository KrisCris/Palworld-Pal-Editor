// The loaded save and the state that follows from it (spec §10).
//
// Three things live here and nothing else does: what save is open, which screen
// the app is on, and whether a write is in flight. Everything the editor shows is
// derived from a session, so this store is what the others read to know whether
// their data is still worth anything.
//
// It reports no errors of its own. An operation that fails throws its `ApiError`
// to whoever started it, because the caller is the one that knows what the user
// was trying to do and which message says so.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { getSession, postSessionSave, putSession } from "../api/session.js";
import {
    backendStorageKey,
    readStorage,
    removeStorage,
    writeStorage,
} from "../services/backend-connection.js";

const EMPTY_SESSION = Object.freeze({ loaded: false, path: null, warnings: [] });

export const useSessionStore = defineStore("session", () => {
    const session = ref({ ...EMPTY_SESSION });
    const appState = ref("connecting");
    // Whether the editor is showing a save, which is not the same as the backend
    // having one open: between `PUT /api/session` and the end of hydration the
    // save exists but the rosters behind it do not yet.
    const editorOpen = computed(() => appState.value === "editor");

    // The path the user picked to load, and the path a save writes back to. They
    // are separate because "save as" exists: the second only follows the first
    // until someone changes it.
    const savePath = ref(null);
    const writeBackPath = ref("");

    // Which session the app is currently showing. A read started against one
    // session must not land on the next: it bumps on every load and every reset,
    // so a caller compares what it captured before the request with what is
    // current after it. The controller aborts whatever is still in flight, which
    // is the cheaper half of the same guarantee -- the epoch is what makes it
    // correct when a response was already on the wire.
    const sessionEpoch = ref(0);
    let inFlight = new AbortController();

    // Every write holds the whole UI, per spec §8.8: while one is running no
    // control anywhere can start a second or edit what the first is about to
    // send. Nested calls share the gate -- an operation built out of two others
    // must not open it halfway through -- so this counts depth rather than
    // flipping a flag.
    const operationPending = ref(false);
    let operationDepth = 0;

    async function runOperation(operation) {
        operationDepth += 1;
        operationPending.value = true;
        try {
            return await operation();
        } finally {
            operationDepth -= 1;
            if (operationDepth === 0) operationPending.value = false;
        }
    }

    // What a read should pass so it is dropped when its session goes away.
    function readOptions() {
        return { signal: inFlight.signal };
    }

    function isCurrentSession(epoch) {
        return epoch === sessionEpoch.value;
    }

    function abandonSession() {
        inFlight.abort();
        inFlight = new AbortController();
        sessionEpoch.value += 1;
        session.value = { ...EMPTY_SESSION };
    }

    async function refreshSession() {
        session.value = await getSession(readOptions());
        return session.value.loaded;
    }

    // Replace whatever is open with the save at `path`. The old session is
    // abandoned first: from here on nothing that was already in flight for it can
    // reach the screen, whether or not this load turns out to succeed.
    async function loadSave(path) {
        abandonSession();
        session.value = await putSession(path);
        savePath.value = session.value.path;
        writeBackPath.value = session.value.path;
        return session.value.loaded;
    }

    // Answers with the path that was written, which is what the caller tells the
    // user -- not the path it asked for, so a save that landed somewhere else
    // cannot be reported as if it had not. A failure throws its `ApiError` like
    // everything else here.
    async function writeSave(path = writeBackPath.value) {
        const saved = await postSessionSave(path);
        return saved.path;
    }

    function rememberSavePath(storage, origin) {
        writeStorage(
            storage,
            backendStorageKey("PAL_GAME_SAVE_PATH", origin),
            savePath.value,
        );
    }

    function forgetSavePath(storage, origin) {
        savePath.value = null;
        removeStorage(storage, backendStorageKey("PAL_GAME_SAVE_PATH", origin));
    }

    function recallSavePath(storage, origin) {
        savePath.value = readStorage(
            storage,
            backendStorageKey("PAL_GAME_SAVE_PATH", origin),
        );
        return savePath.value;
    }

    return {
        session,
        appState,
        editorOpen,
        savePath,
        writeBackPath,
        sessionEpoch,
        operationPending,

        runOperation,
        readOptions,
        isCurrentSession,
        refreshSession,
        loadSave,
        writeSave,
        rememberSavePath,
        forgetSavePath,
        recallSavePath,
    };
});
