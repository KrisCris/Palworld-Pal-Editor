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

const { usePalEditorStore } = await import("../src/stores/paleditor.js");
const { useSessionStore } = await import("../src/stores/session.js");
let session;

function newStore() {
    setActivePinia(createPinia());
    session = useSessionStore();
    return usePalEditorStore();
}

test("dumping Pal data only copies JSON and reports success", async t => {
    const originalPost = axios.post;
    let copied;
    let opened = false;
    axios.post = async () => ({ data: { status: 0, data: '{"CharacterID":"SheepBall"}' } });
    Object.defineProperty(globalThis.navigator, "clipboard", {
        configurable: true,
        value: { writeText: async value => { copied = value; } },
    });
    window.open = () => { opened = true; };
    t.after(() => { axios.post = originalPost; });

    const store = newStore();
    await store.dumpPalData();

    assert.equal(copied, '{"CharacterID":"SheepBall"}');
    assert.equal(opened, false);
    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Pal_Copied");
    assert.equal(store.CURRENT_MESSAGE.presentation, "toast");
    assert.equal(session.operationPending, false);
});

test("clipboard failures use the normal error dialog and release loading", async t => {
    const originalPost = axios.post;
    const originalConsoleError = console.error;
    axios.post = async () => ({ data: { status: 0, data: "{}" } });
    Object.defineProperty(globalThis.navigator, "clipboard", {
        configurable: true,
        value: { writeText: async () => { throw new Error("clipboard denied"); } },
    });
    console.error = () => {};
    t.after(() => {
        axios.post = originalPost;
        console.error = originalConsoleError;
    });

    const store = newStore();
    await store.dumpPalData();

    assert.equal(store.CURRENT_MESSAGE.presentation, "dialog");
    assert.equal(store.CURRENT_MESSAGE.code, "Error");
    assert.match(store.CURRENT_MESSAGE.log, /clipboard denied/);
    assert.equal(session.operationPending, false);
});
