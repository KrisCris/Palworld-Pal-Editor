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
const { useAppStore } = await import("../src/stores/app.js");
const { GAME_LANGUAGES, UI_TRANSLATIONS } = await import("../src/i18n/index.js");
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

test("Pal upgrade section titles match the game UI terminology", () => {
    assert.deepEqual(
        [en.Editor_IV, en.Editor_Souls_Upgrade, en.Editor_Condenser],
        ["Potential", "Enhance Pals", "Pal Condensation"],
    );
    assert.deepEqual(
        [fr.Editor_IV, fr.Editor_Souls_Upgrade, fr.Editor_Condenser],
        ["Potentiel", "Améliorer un Pal", "Enrichissement de Pal"],
    );
    assert.deepEqual(
        [ja.Editor_IV, ja.Editor_Souls_Upgrade, ja.Editor_Condenser],
        ["ポテンシャル", "パル強化", "パル濃縮"],
    );
    assert.deepEqual(
        [zhCN.Editor_IV, zhCN.Editor_Souls_Upgrade, zhCN.Editor_Condenser],
        ["潜力", "强化帕鲁", "帕鲁浓缩"],
    );
});

test("startup translations are available synchronously without the backend", () => {
    setActivePinia(createPinia());
    const store = usePalEditorStore();

    assert.equal(typeof store.getTranslatedText("BackendError_Title"), "string");
    assert.notEqual(store.getTranslatedText("BackendError_Title"), "I18N_MISSING");
    assert.deepEqual(useAppStore().localeOptions, {
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

test("backend connection failures explain browser and server requirements", () => {
    for (const detail of ["HTTPS", "CORS", "password", "Local Network Access"]) {
        assert.match(en.BackendSelector_Connection_Failed, new RegExp(detail, "i"));
    }
});

test("offline and backend game-data locale maps stay identical", async () => {
    const backendLanguages = JSON.parse(await readFile(
        new URL("../../../src/palworld_pal_editor/assets/data/i18n_list.json", import.meta.url),
        "utf8",
    ));

    assert.deepEqual(GAME_LANGUAGES, backendLanguages);
});

test("saved game-data locales use their complete frontend translation", () => {
    values.set("PAL_I18n", "zh-TW");
    setActivePinia(createPinia());
    const store = usePalEditorStore();

    assert.equal(useAppStore().locale, "zh-TW");
    assert.equal(store.getTranslatedText("BackendError_Title"), UI_TRANSLATIONS["zh-TW"].BackendError_Title);
});

test("the anti-scam warning is not restricted to Chinese", async () => {
    const source = await readFile(new URL("../src/stores/paleditor.js", import.meta.url), "utf8");
    assert.doesNotMatch(source, /app\.locale\s*==={0,1}\s*["']zh-CN["']/);
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
        "Editor_Suitabilities_Max",
        "Editor_Container_DimensionalPalStorage",
        "Editor_Container_GlobalPalbox",
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
        "BackendSelector_Label",
        "BackendSelector_Title",
        "BackendSelector_Description",
        "BackendSelector_Connected",
        "BackendSelector_Disconnected",
        "BackendSelector_Recent",
        "BackendSelector_Current",
        "BackendSelector_Other",
        "BackendSelector_Address",
        "BackendSelector_Connect",
        "BackendSelector_Use_Page_Server",
        "BackendSelector_Remove",
        "BackendSelector_Invalid_Address",
        "BackendSelector_Connection_Failed",
        "SkillTemplate_Expand",
        "SkillTemplate_Collapse",
        "BackendSelector_Cors_Hint",
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
        "Message_Skill_Equip_Full",
        "Message_Invalid_Suitability",
        "Message_Select_Player",
        "Message_No_Player",
        "Message_Select_Pal_Failed",
        "Message_Save_Success",
        "Message_Pal_Copied",
        "Message_AntiScam",
        "SupportDialog_Title",
        "SupportDialog_Intro",
        "SupportDialog_Financial_Title",
        "SupportDialog_Financial_Description",
        "SupportDialog_Other_Title",
        "SupportDialog_Other_Description",
        "SupportDialog_QR_Alt",
        "SupportDialog_Payment_Title",
        "SupportDialog_Online_Description",
        "SupportDialog_QR_Description",
        "SupportDialog_Open_Payment",
        "SupportDialog_Open_QR",
        "SupportDialog_QR_Title",
        "SupportDialog_Not_Now",
        "SupportDialog_View_Project",
        "Operation_Select_Path",
        "Operation_Update_Player",
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
        "Editor_Passive_Category_Pal",
        "Editor_Passive_Category_Regular",
        "Editor_Passive_Category_Partner",
        ...palBasicInfoKeys,
    ];
    for (const locale of Object.values(UI_TRANSLATIONS)) {
        for (const key of keys) {
            assert.equal(typeof locale[key], "string", key);
            assert.notEqual(locale[key], "", key);
        }
    }
});

// Carried over from the deleted `test_entry_view_ui.py`, which checked these in
// four locales by reading the .js files as text. The entry page is the first
// thing anyone sees, so an untranslated string there is the most visible kind.
test("the entry page is translated in every locale", () => {
    const keys = [
        "Entry_Title", "Entry_Intro", "Entry_Help",
        "Entry_Support_Title", "Entry_Support_Subtitle",
        "Entry_Support_Community_Title", "Entry_Support_Community_Description",
        "Entry_Support_Code_Title", "Entry_Support_Code_Description",
        "Entry_Support_Issue_Title", "Entry_Support_Issue_Description",
        "Entry_Support_Author_Title", "Entry_Support_Author_Description",
        "Entry_Downloads_Title", "Entry_Downloads_Subtitle",
        "Entry_Download_GitHub_Description", "Entry_Download_Nexus_Description",
        "Entry_Download_Bilibili_Description",
        "Entry_Load_Title", "Entry_Load_Subtitle", "Entry_Path_Label",
        "Entry_Instructions_Title", "Entry_Instructions_Subtitle",
        "Entry_Instruction_First_Title", "Entry_Instruction_First_Description",
        "Entry_Instruction_WebUI_Title", "Entry_Instruction_WebUI_Description",
        "Entry_Instruction_Docker_Title", "Entry_Instruction_Docker_Description",
    ];
    for (const locale of Object.values(UI_TRANSLATIONS)) {
        for (const key of keys) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});

test("roster collapse controls are translated in every locale", () => {
    for (const locale of Object.values(UI_TRANSLATIONS)) {
        for (const key of ["PlayerList_Collapse", "PlayerList_Restore", "PalList_Collapse", "PalList_Restore"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
