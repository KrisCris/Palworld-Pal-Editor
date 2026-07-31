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

test("blocking dialogs render their existing severity semantics", () => {
    const store = newStore();
    store.showMessage({
        severity: "warning",
        presentation: "dialog",
        messageKey: "Message_CN_AntiScam",
    });

    assert.equal(store.CURRENT_MESSAGE.severity, "warning");
    assert.match(messageCenterSource, /:class="\['message-dialog', current\.severity\]"/);
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

    store.I18n = "en";
    assert.equal(store.getMessageText(store.CURRENT_MESSAGE), "updating the Pal failed.");
    store.I18n = "zh-CN";
    assert.equal(store.getMessageText(store.CURRENT_MESSAGE), "更新帕鲁失败。");
});

test("frontend errors retain editor state and expose their stack", t => {
    const store = newStore();
    const originalState = store.APP_STATE;
    const originalConsoleError = console.error;
    console.error = () => {};
    t.after(() => { console.error = originalConsoleError; });

    store.reportFrontendError(new TypeError("broken renderer"), "Vue render");

    assert.equal(store.APP_STATE, originalState);
    assert.equal(store.CURRENT_MESSAGE.code, "TypeError");
    assert.match(store.CURRENT_MESSAGE.log, /broken renderer/);
});
