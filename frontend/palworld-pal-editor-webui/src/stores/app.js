// The app's own settings, independent of any save.
//
// Startup config, the save-path picker, the language preference and the update
// check: four small things in one store rather than one store each, because none
// of them is big enough to earn a module and all of them are answered by one
// blueprint.
//
// Nothing here reads or holds save data. Like `stores/session`, it reports no
// errors of its own -- a failed call throws its `ApiError` to whoever started it,
// since the caller is what knows which message describes what the user was doing.

import { ref, watch } from "vue";
import { defineStore } from "pinia";

import {
    browseSavePaths,
    getAppConfig,
    getLatestRelease,
    patchAppConfig,
} from "../api/app.js";
import { GAME_LANGUAGES } from "../i18n/index.js";

const LOCALE_STORAGE_KEY = "PAL_I18n";

export const useAppStore = defineStore("app", () => {
    // The locale is remembered locally as well as on the server, because it
    // decides what the entry screen says before any request has answered.
    const storedLocale = localStorage.getItem(LOCALE_STORAGE_KEY);
    const locale = ref(GAME_LANGUAGES[storedLocale] ? storedLocale : "en");
    const localeOptions = ref(GAME_LANGUAGES);

    const version = ref("0.0.0");
    const isOfficialBuild = ref(false);
    const hasPassword = ref(false);
    // What the backend is configured to load. Distinct from `session.savePath`,
    // which is what this client last chose.
    const defaultSavePath = ref("");
    const donationPromptDismissed = ref(false);

    // `{updateAvailable, version, downloadUrl, nexusUrl}`. "No update" is one of
    // the answers, not a failure, so this is never empty after it loads.
    const latestRelease = ref({});

    // The save-path picker. `pickerParentPath` is the backend's answer for "up",
    // which is why walking the tree needs no state on the server.
    const pickerOpen = ref(false);
    const pickerPath = ref("");
    const pickerParentPath = ref("");
    const pickerEntries = ref(new Map());
    const pickerIsSaveDir = ref(false);

    // The choice belongs to this browser, so it is written the moment it changes
    // -- including on the auth screen, where there is no token to tell the
    // backend with and `pushLocale` never runs.
    watch(locale, value => localStorage.setItem(LOCALE_STORAGE_KEY, value));

    function applyConfig(config) {
        localeOptions.value = config.i18nOptions;
        // A locale the user picked here beats the server's: it is this browser's
        // preference, and the server's is whatever the last client set.
        if (!localStorage.getItem(LOCALE_STORAGE_KEY) && config.i18nOptions[config.i18n]) {
            locale.value = config.i18n;
        }
        defaultSavePath.value = config.defaultSavePath;
        hasPassword.value = config.hasPassword;
        version.value = config.version;
        isOfficialBuild.value = config.isOfficialBuild;
        donationPromptDismissed.value = config.donationPromptDismissed;
    }

    async function loadConfig() {
        applyConfig(await getAppConfig());
    }

    // Tell the backend which language to answer in. The reply is the whole
    // config, which is how the donation prompt's state follows the language --
    // it is remembered per locale.
    async function pushLocale() {
        applyConfig(await patchAppConfig({ i18n: locale.value }));
    }

    async function dismissDonationPrompt() {
        applyConfig(await patchAppConfig({ donationPromptDismissed: true }));
    }

    async function loadLatestRelease() {
        latestRelease.value = await getLatestRelease();
    }

    // `path` omitted means "wherever the backend opens by default".
    async function browse(path) {
        const context = await browseSavePaths(path);
        pickerPath.value = context.currentPath;
        pickerParentPath.value = context.parentPath;
        pickerEntries.value = new Map(Object.entries(context.children));
        pickerIsSaveDir.value = context.isPalDir;
        pickerOpen.value = true;
    }

    function closePicker() {
        pickerOpen.value = false;
    }

    return {
        locale,
        localeOptions,
        version,
        isOfficialBuild,
        hasPassword,
        defaultSavePath,
        donationPromptDismissed,
        latestRelease,
        pickerOpen,
        pickerPath,
        pickerParentPath,
        pickerEntries,
        pickerIsSaveDir,

        loadConfig,
        pushLocale,
        dismissDonationPrompt,
        loadLatestRelease,
        browse,
        closePicker,
    };
});
