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
        "Message_Title_Success",
        "Message_Title_Warning",
        "Message_Title_Error",
        "Message_Close",
        "Message_Details",
        "Message_Operation_Failed",
        "Message_Unexpected_Frontend_Error",
        "AuthView_Session_Expired",
        "Message_Select_Skill",
        "Message_Passive_Limit",
        "Message_Invalid_Suitability",
        "Message_Select_Player",
        "Message_No_Player",
        "Message_Select_Pal_Failed",
        "Message_Basecamp_Add_Unsupported",
        "Message_Save_Success",
        "Message_Pal_Copied",
        "Message_CN_AntiScam",
        "Operation_Select_Path",
        "Operation_Update_Player",
        "Operation_Load_Player",
        "Operation_Save",
        "Operation_Load_Pals",
        "Operation_Load_Player_Data",
        "Operation_Load_Pal",
        "Operation_Update_Pal",
        "Operation_Copy_Pal",
        "Operation_Delete_Pal",
        "Operation_Add_Pal",
        "Operation_Duplicate_Pal",
        "Operation_Donation",
    ];
    for (const { default: locale } of locales) {
        for (const key of keys) assert.equal(typeof locale[key], "string", key);
    }
});
