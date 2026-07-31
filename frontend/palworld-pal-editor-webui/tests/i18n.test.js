import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { createPinia, setActivePinia } from "pinia";

const values = new Map([["PAL_I18n", "zh-CN"]]);
globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
};

const { usePalEditorStore } = await import("../src/stores/paleditor.js");
const { GAME_LANGUAGES } = await import("../src/i18n/index.js");
const locales = await Promise.all([
    import("../src/i18n/en.js"),
    import("../src/i18n/fr.js"),
    import("../src/i18n/ja.js"),
    import("../src/i18n/zh-CN.js"),
]);
const [{ default: en }, { default: fr }, { default: ja }, { default: zhCN }] = locales;

test("variant labels distinguish Alpha bosses from Lucky Pals", () => {
    assert.equal(en.Editor_Variant_boss, "Alpha");
    assert.equal(en.Editor_Variant_rare, "Lucky");
    assert.equal(fr.Editor_Variant_boss, "Alpha");
    assert.equal(fr.Editor_Variant_rare, "Chanceux");
    assert.equal(ja.Editor_Variant_boss, "ボス");
    assert.equal(ja.Editor_Variant_rare, "希少");
    assert.equal(zhCN.Editor_Variant_boss, "头目");
    assert.equal(zhCN.Editor_Variant_rare, "稀有");
});

test("variant action labels use the same Alpha and Lucky semantics", () => {
    assert.equal(en.Editor_Btn_Toggle_Boss, "Toggle Alpha status");
    assert.equal(en.Editor_Btn_Toggle_Rare, "Toggle Lucky status");
    assert.equal(fr.Editor_Btn_Toggle_Boss, "Basculer le statut Alpha");
    assert.equal(fr.Editor_Btn_Toggle_Rare, "Basculer le statut Chanceux");
    assert.equal(ja.Editor_Btn_Toggle_Boss, "ボス状態を切り替える");
    assert.equal(ja.Editor_Btn_Toggle_Rare, "希少状態を切り替える");
    assert.equal(zhCN.Editor_Btn_Toggle_Boss, "切换头目状态");
    assert.equal(zhCN.Editor_Btn_Toggle_Rare, "切换稀有状态");
});

test("startup translations are available synchronously without the backend", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();

    assert.equal(typeof store.getTranslatedText("BackendError_Title"), "string");
    assert.notEqual(store.getTranslatedText("BackendError_Title"), "I18N_MISSING");
    assert.deepEqual(store.I18nList, {
        en: "English",
        de: "Deutsch",
        es: "Español",
        "es-MX": "Español (México)",
        fr: "Français",
        id: "Bahasa Indonesia",
        it: "Italiano",
        ja: "日本語",
        ko: "한국어",
        pl: "Polski",
        "pt-BR": "Português (Brasil)",
        ru: "Русский",
        th: "ไทย",
        tr: "Türkçe",
        vi: "Tiếng Việt",
        "zh-CN": "简体中文",
        "zh-TW": "繁體中文",
    });
});

test("offline and backend game-data locale maps stay identical", async () => {
    const backendLanguages = JSON.parse(await readFile(
        new URL("../../../src/palworld_pal_editor/assets/data/i18n_list.json", import.meta.url),
        "utf8",
    ));

    assert.deepEqual(GAME_LANGUAGES, backendLanguages);
});

test("saved game-data locales remain selected with English chrome fallback", () => {
    values.set("PAL_I18n", "zh-TW");
    setActivePinia(createPinia());
    const store = usePalEditorStore();

    assert.equal(store.I18n, "zh-TW");
    assert.equal(store.getTranslatedText("BackendError_Title"), "Something went wrong");
});

test("bootstrap, authentication, and error controls are translated in every locale", () => {
    const palBasicInfoKeys = [
        "Editor_Identity_Appearance",
        "Editor_Growth",
        "Editor_Save_Details",
        "Editor_Btn_Friendship_Decrease",
        "Editor_Btn_Friendship_Increase",
        "Editor_Btn_Friendship_Max",
        "Editor_Btn_Level_Decrease",
        "Editor_Btn_Level_Increase",
        "Editor_Btn_Level_Max",
        "Editor_Btn_Toggle_Boss",
        "Editor_Btn_Toggle_Rare",
    ];
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
        ...palBasicInfoKeys,
    ];
    for (const { default: locale } of locales) {
        for (const key of keys) {
            assert.equal(typeof locale[key], "string", key);
            assert.notEqual(locale[key], "", key);
        }
    }
});

test("roster collapse controls are translated in every locale", () => {
    for (const { default: locale } of locales) {
        for (const key of ["PlayerList_Collapse", "PlayerList_Restore", "PalList_Collapse", "PalList_Restore"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
