import assert from "node:assert/strict";
import test from "node:test";

import axios from "axios";
import { createPinia, setActivePinia } from "pinia";

globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
};
globalThis.window = { location: { origin: "http://frontend.test" } };

const { useMessagesStore } = await import("../src/stores/messages.js");
const { usePalsStore } = await import("../src/stores/pals.js");
const { useSessionStore } = await import("../src/stores/session.js");
let session;
let messages;

// The export button reads the Pal that is open, so these need one open.
const RECORD_KEY = "world:pal-1";
const NATIVE_RECORD = { key: { InstanceId: "pal-1" }, value: { CharacterID: "SheepBall" } };

function newStore() {
    setActivePinia(createPinia());
    session = useSessionStore();
    messages = useMessagesStore();
    const pals = usePalsStore();
    pals.selectedRecordKey = RECORD_KEY;
    return pals;
}

test("dumping Pal data only copies JSON and reports success", async t => {
    const originalGet = axios.get;
    let requested;
    let copied;
    let opened = false;
    axios.get = async url => {
        requested = url;
        return { data: NATIVE_RECORD };
    };
    Object.defineProperty(globalThis.navigator, "clipboard", {
        configurable: true,
        value: { writeText: async value => { copied = value; } },
    });
    window.open = () => { opened = true; };
    t.after(() => { axios.get = originalGet; });

    const store = newStore();
    await store.copyNativeRecord();

    assert.equal(requested, `/api/pals/${encodeURIComponent(RECORD_KEY)}/native-record`);
    // The record crosses the wire; the indentation is a property of what lands
    // on the clipboard, so it is added here rather than by the backend.
    assert.equal(copied, JSON.stringify(NATIVE_RECORD, null, 4));
    assert.equal(opened, false);
    assert.equal(messages.CURRENT_MESSAGE.messageKey, "Message_Pal_Copied");
    assert.equal(messages.CURRENT_MESSAGE.presentation, "toast");
    assert.equal(session.operationPending, false);
});

test("clipboard failures use the normal error dialog and release loading", async t => {
    const originalGet = axios.get;
    const originalConsoleError = console.error;
    axios.get = async () => ({ data: NATIVE_RECORD });
    Object.defineProperty(globalThis.navigator, "clipboard", {
        configurable: true,
        value: { writeText: async () => { throw new Error("clipboard denied"); } },
    });
    console.error = () => {};
    t.after(() => {
        axios.get = originalGet;
        console.error = originalConsoleError;
    });

    const store = newStore();
    await store.copyNativeRecord();

    assert.equal(messages.CURRENT_MESSAGE.presentation, "dialog");
    assert.equal(messages.CURRENT_MESSAGE.code, "Error");
    assert.match(messages.CURRENT_MESSAGE.log, /clipboard denied/);
    assert.equal(session.operationPending, false);
});
