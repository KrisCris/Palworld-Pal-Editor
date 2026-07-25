import assert from "node:assert/strict";
import test from "node:test";

import { createPinia, setActivePinia } from "pinia";

const values = new Map([["PAL_I18n", "zh-CN"]]);
globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
};

const { usePalEditorStore } = await import("../src/stores/paleditor.js");
const locales = await Promise.all([
    import("../src/i18n/en.js"),
    import("../src/i18n/fr.js"),
    import("../src/i18n/ja.js"),
    import("../src/i18n/zh-CN.js"),
]);

test("startup translations are available synchronously without the backend", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();

    assert.equal(typeof store.getTranslatedText("BackendError_Title"), "string");
    assert.notEqual(store.getTranslatedText("BackendError_Title"), "I18N_MISSING");
    assert.deepEqual(store.I18nList, {
        en: "English",
        "zh-CN": "中文",
        ja: "日本語",
        fr: "Français",
    });
});

test("bootstrap, authentication, and error controls are translated in every locale", () => {
    const keys = [
        "App_Connecting",
        "AuthView_Password_Label",
        "AuthView_Remember_7_Days",
        "AuthView_Wrong_Password",
        "BackendError_Logo_Alt",
        "BackendError_Title",
        "BackendError_Connection_Title",
        "BackendError_Request_Failed",
        "BackendError_Startup",
        "BackendError_Application_Startup",
        "BackendError_Runtime",
        "BackendError_Connection_Runtime",
        "BackendError_Details",
        "BackendError_Refresh",
        "BackendError_Dismiss",
        "TopBar_Language_Label",
    ];
    for (const { default: locale } of locales) {
        for (const key of keys) assert.equal(typeof locale[key], "string", key);
    }
});
