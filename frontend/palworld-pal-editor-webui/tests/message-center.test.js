import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { createPinia, setActivePinia } from "pinia";

globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
};

const { usePalEditorStore } = await import("../src/stores/paleditor.js");
const { useAppStore } = await import("../src/stores/app.js");
const { useSessionStore } = await import("../src/stores/session.js");
const messageCenterSource = await readFile(
    new URL("../src/components/MessageCenter.vue", import.meta.url),
    "utf8",
);

function newStore() {
    setActivePinia(createPinia());
    return usePalEditorStore();
}

test("dialogs interrupt toasts without reversing either queue", () => {
    const store = newStore();
    const toast = store.showMessage({
        severity: "success",
        presentation: "toast",
        messageKey: "Message_Save_Success",
    });
    const firstDialog = store.showMessage({
        severity: "error",
        presentation: "dialog",
        message: "first",
    });
    const secondDialog = store.showMessage({
        severity: "error",
        presentation: "dialog",
        message: "second",
    });

    assert.deepEqual(
        store.MESSAGE_QUEUE.map(message => message.id),
        [firstDialog, secondDialog, toast],
    );
    assert.equal(store.CURRENT_MESSAGE.message, "first");
    store.dismissMessage(firstDialog);
    assert.equal(store.CURRENT_MESSAGE.message, "second");
});

test("confirmation messages resolve through the custom dialog actions", async () => {
    const store = newStore();
    const confirmation = store.confirmMessage("Message_AntiScam");

    assert.equal(store.CURRENT_MESSAGE.confirmation, true);
    store.respondToMessage(store.CURRENT_MESSAGE.id, false);
    assert.equal(await confirmation, false);

    const secondConfirmation = store.confirmMessage("Message_AntiScam");
    store.dismissMessage(store.CURRENT_MESSAGE.id);
    assert.equal(await secondConfirmation, false);
});

test("blocking dialogs render their existing severity semantics", () => {
    const store = newStore();
    store.showMessage({
        severity: "warning",
        presentation: "dialog",
        messageKey: "Message_AntiScam",
    });

    assert.equal(store.CURRENT_MESSAGE.severity, "warning");
    assert.match(
        messageCenterSource,
        /:class="\['message-dialog', 'editor-glass-surface', current\.severity\]"/,
    );
    assert.match(messageCenterSource, /@pointerdown\.self="dismiss"/);
    assert.match(messageCenterSource, /cancelButton\.value\?\.focus\(\)/);
    assert.match(messageCenterSource, /\.message-dialog button:focus-visible/);
    for (const [severity, token] of Object.entries({
        warning: "warning",
        success: "success",
        error: "danger",
    })) {
        assert.match(
            messageCenterSource,
            new RegExp(`\\.message-dialog\\.${severity}\\s*\\{[^}]*var\\(--editor-color-${token}\\)`, "s"),
        );
    }
});

test("messages stay above editor dialogs", () => {
    const skillTemplateSource = readFile(
        new URL("../src/components/SkillTemplateDialog.vue", import.meta.url),
        "utf8",
    );
    return skillTemplateSource.then(source => {
        const messageLayer = Number(messageCenterSource.match(/\.message-layer\s*\{[\s\S]*?z-index:\s*(\d+)/)?.[1]);
        const messageToast = Number(messageCenterSource.match(/\.message-toast\s*\{[\s\S]*?z-index:\s*(\d+)/)?.[1]);
        const skillDialog = Number(source.match(/\.skill-template-layer\s*\{[\s\S]*?z-index:\s*(\d+)/)?.[1]);
        assert.ok(messageLayer > skillDialog, `${messageLayer} should exceed ${skillDialog}`);
        assert.ok(messageToast > skillDialog, `${messageToast} should exceed ${skillDialog}`);
    });
});

test("operation errors retain backend diagnostics and translatable context", () => {
    const store = newStore();

    store.reportOperationError("Operation_Update_Pal", {
        msg: "invalid Pal state",
        data: { error: { code: "InvalidPal" } },
    });

    assert.equal(store.CURRENT_MESSAGE.presentation, "dialog");
    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Operation_Failed");
    assert.deepEqual(store.CURRENT_MESSAGE.args, [
        { translationKey: "Operation_Update_Pal" },
    ]);
    assert.equal(store.CURRENT_MESSAGE.code, "InvalidPal");
    assert.equal(store.CURRENT_MESSAGE.log, "invalid Pal state");

    useAppStore().locale = "en";
    assert.equal(store.getMessageText(store.CURRENT_MESSAGE), "updating the Pal failed.");
    useAppStore().locale = "zh-CN";
    assert.equal(store.getMessageText(store.CURRENT_MESSAGE), "更新帕鲁失败。");
});

test("frontend errors retain editor state and expose their stack", t => {
    const store = newStore();
    const originalState = useSessionStore().appState;
    const originalConsoleError = console.error;
    console.error = () => {};
    t.after(() => { console.error = originalConsoleError; });

    store.reportFrontendError(new TypeError("broken renderer"), "Vue render");

    assert.equal(useSessionStore().appState, originalState);
    assert.equal(store.CURRENT_MESSAGE.code, "TypeError");
    assert.match(store.CURRENT_MESSAGE.log, /broken renderer/);
});
