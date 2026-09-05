// Bringing the app up, and putting a save in front of the user.
//
// Choosing a backend, authenticating against it, opening a save and hydrating
// everything the editor reads from one, writing it back, and running the cascade
// a language change sets off. Every step here spans stores that know nothing of
// each other, which is what makes it a step and not a store method.
//
// It owns almost nothing. The connection and the token are `stores/backend`, the
// message queue is `stores/messages`, the save is `stores/session`, and its Pals,
// players, rosters and storages are the stores below. This one reads them all,
// and nothing reads back into it -- which is why every one of them can report a
// failure without importing it.

import { ref, computed } from "vue";
import { defineStore, storeToRefs } from "pinia";
// Only `connectBackend`'s probe uses this directly: it asks a candidate origin
// the store has not adopted yet, with no token and its own timeout, which is
// exactly what `api/http.js` cannot express.
import axios from "axios";
import {
    backendUrl,
    normalizeBackendOrigin,
    readRecentBackends,
    readStorage,
    rememberBackend,
    writeStorage,
} from "../services/backend-connection.js";
import { translate } from "../i18n/index.js";
import { checkAuth, login } from "../api/auth.js";
import { useAppStore } from "./app.js";
import { BACKEND_ORIGIN_KEY, useBackendStore } from "./backend.js";
import { useCatalogsStore } from "./catalogs.js";
import { useMessagesStore } from "./messages.js";
import { usePalsStore } from "./pals.js";
import { useResearchStore } from "./research.js";
import { usePlayersStore } from "./players.js";
import { BASE_ROSTER_KEY, useRostersStore } from "./rosters.js";
import { gated, useSessionStore } from "./session.js";
import { useStoragesStore } from "./storages.js";
import { useTemplatesStore } from "./templates.js";

export const usePalEditorStore = defineStore("paleditor", () => {
    const session = useSessionStore();
    const app = useAppStore();
    const backend = useBackendStore();
    const messages = useMessagesStore();
    const catalogs = useCatalogsStore();
    const pals = usePalsStore();
    const research = useResearchStore();
    const players = usePlayersStore();
    const rosters = useRostersStore();
    const storages = useStoragesStore();
    const templates = useTemplatesStore();

    // flags
    const SHOW_DONATE_FLAG = ref(false);

    // A base camp is worth listing even when nobody works in it yet, so the base
    // roster button follows the storages as well as the roster listing.
    const HAS_WORKING_PAL_FLAG = computed(
        () => rosters.hasBaseRoster || storages.hasBaseStorage,
    );

    // The connection, the token and what a failed request means live in
    // `stores/backend`; the message queue in `stores/messages`. Both are read
    // here rather than owned here, so that every other store can report through
    // them without importing this one.
    const {
        BACKEND_ORIGIN,
        BACKEND_CANDIDATE,
        BACKEND_REQUEST_ORIGIN,
        BACKEND_RECENT,
        BACKEND_CONNECTED,
        BACKEND_ERROR,
        IS_LOCKED,
        AUTH_MESSAGE_KEY,
        AUTH_TOKEN,
    } = storeToRefs(backend);
    const {
        normalizeStoredBackendOrigin,
        storageKey,
        setAuthToken,
        rememberAuthToken,
        reloadAuthToken,
        setBackendError,
        clearBackendError,
        requireAuth,
        reportApiFailure,
        reportStartupFailure,
    } = backend;
    const { showMessage, showToast } = messages;

    // Reading the remembered path is what puts it back on `session`; the picker
    // opens on it, which is why the answer is kept.
    app.pickerPath = session.recallSavePath(localStorage, BACKEND_ORIGIN.value);

    const CN_WARNING_ON_LOAD = ref(true);

    async function auth() {
        // The endpoint answers 200 only for a token the backend still accepts, so
        // there is nothing in the body to check: reaching the next line is the yes.
        try {
            await checkAuth();
        } catch (error) {
            if (error.isAuthFailure) requireAuth("AuthView_Session_Expired");
            else reportStartupFailure(error);
            return false;
        }
        IS_LOCKED.value = false;
        return true;
    }

    async function unlock(password, remember = false) {
        AUTH_MESSAGE_KEY.value = "";
        session.appState = "connecting";
        let response;
        try {
            response = await login(password, remember);
        } catch (error) {
            // A wrong password is answered with 401, so the refusal arrives as a
            // thrown error rather than as a field in a 200 body.
            if (error.isAuthFailure) requireAuth("AuthView_Wrong_Password");
            else reportStartupFailure(error);
            return false;
        }
        IS_LOCKED.value = false;
        setAuthToken(response.data.access_token);
        rememberAuthToken(remember);
        session.appState = "connecting";
        return await resumeBackendSave();
    }

    function promoteBackend(origin) {
        origin = normalizeStoredBackendOrigin(origin);
        const changed = origin !== BACKEND_ORIGIN.value;
        BACKEND_ORIGIN.value = origin;
        BACKEND_REQUEST_ORIGIN.value = origin;
        writeStorage(localStorage, BACKEND_ORIGIN_KEY, origin);
        BACKEND_RECENT.value = origin
            ? rememberBackend(localStorage, origin)
            : readRecentBackends(localStorage);
        if (changed) {
            templates.clear();
            reloadAuthToken();
            app.pickerPath = session.recallSavePath(localStorage, origin);
        }
    }

    // The first call the app makes and the only one that needs no token: it is
    // how the client learns whether it has to authenticate at all.
    async function loadAppConfig(origin = BACKEND_REQUEST_ORIGIN.value) {
        try {
            await app.loadConfig();
        } catch (error) {
            reportStartupFailure(error);
            return false;
        }
        promoteBackend(origin);
        BACKEND_CONNECTED.value = true;
        // Only if this client has not already chosen one: the backend's path is
        // whatever it was last configured with, not what this browser last used.
        if (!session.savePath) session.savePath = app.defaultSavePath;
        return true;
    }

    async function resumeBackendSave() {
        let loaded;
        try {
            loaded = await session.refreshSession();
        } catch (error) {
            reportStartupFailure(error);
            return false;
        }
        if (loaded) {
            if (app.defaultSavePath) {
                session.savePath = app.defaultSavePath;
                session.writeBackPath = app.defaultSavePath;
            }
            return await hydrateLoadedSave();
        }
        reset();
        session.appState = "entry";
        return true;
    }

    async function bootstrap(candidate = readStorage(localStorage, BACKEND_ORIGIN_KEY) || "") {
        candidate = normalizeStoredBackendOrigin(candidate);
        session.appState = "connecting";
        IS_LOCKED.value = true;
        BACKEND_CONNECTED.value = false;
        clearBackendError();
        BACKEND_CANDIDATE.value = candidate;
        BACKEND_REQUEST_ORIGIN.value = candidate;
        if (candidate !== BACKEND_ORIGIN.value) setAuthToken("");
        else setAuthToken(AUTH_TOKEN.value || readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");

        if (!await loadAppConfig(BACKEND_CANDIDATE.value)) {
            BACKEND_REQUEST_ORIGIN.value = BACKEND_ORIGIN.value;
            return false;
        }
        if (app.hasPassword) {
            if (!AUTH_TOKEN.value) {
                session.appState = "auth-required";
                return true;
            }
            if (!await auth()) {
                return false;
            }
            return await resumeBackendSave();
        }
        return await unlock("", false);
    }

    async function connectBackend(candidate) {
        if (session.appState === "editor") return false;
        const previousOrigin = BACKEND_ORIGIN.value;
        const previousToken = AUTH_TOKEN.value;
        const wasConnected = BACKEND_CONNECTED.value;
        candidate = normalizeBackendOrigin(candidate, window.location.origin);
        try {
            const probe = await axios.get(backendUrl(candidate, "/api/app-config"), { timeout: 5000 });
            // Something answered; `version` is what says it was a Pal Editor.
            if (!probe.data?.version) {
                return false;
            }
        } catch {
            return false;
        }
        BACKEND_CANDIDATE.value = candidate;
        clearBackendError();
        session.appState = "connecting";
        await bootstrap(BACKEND_CANDIDATE.value);
        if (BACKEND_ORIGIN.value === previousOrigin && BACKEND_ORIGIN.value !== candidate) {
            setAuthToken(previousToken);
            BACKEND_CANDIDATE.value = previousOrigin;
            BACKEND_REQUEST_ORIGIN.value = previousOrigin;
            BACKEND_CONNECTED.value = wasConnected;
        }
        return BACKEND_ORIGIN.value === candidate;
    }

    // The entry screen asks on mount. Whether a newer build exists is not worth
    // interrupting anyone over, so a failure here stays where it happened -- the
    // notice simply does not appear, exactly as when there is no update.
    async function loadLatestRelease() {
        try {
            await app.loadLatestRelease();
        } catch {
            // Deliberately nothing: see above.
        }
    }

    // `path` omitted opens wherever the backend keeps saves.
    async function browseSavePath(path) {
        try {
            await app.browse(path);
        } catch (error) {
            reportApiFailure(error, "Operation_Select_Path");
        }
    }

    async function openFilePicker() {
        try {
            await app.browse(session.savePath || undefined);
        } catch (error) {
            // A remembered path whose directory is gone is not worth a dialog:
            // forget it and open where the backend would have.
            if (error.code === "PATH_NOT_FOUND") {
                session.forgetSavePath(localStorage, BACKEND_ORIGIN.value);
                await browseSavePath();
                return;
            }
            reportApiFailure(error, "Operation_Select_Path");
        }
    }

    // The backend answers a filesystem root with itself, so this stops there
    // rather than looping.
    function browseParentPath() {
        return browseSavePath(app.pickerParentPath);
    }

    // `app.locale` is already the new value -- the language select writes it and
    // the app store persists it. This is the cascade that follows: tell the
    // backend, then re-read everything the backend translates.
    async function updateI18n() {
        if (IS_LOCKED.value || BACKEND_ERROR.value) return true;

        sorryandfuckyou();

        try {
            await app.pushLocale();
        } catch (error) {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [error.message]));
            return false;
        }

        let refreshSucceeded = true;
        {
            // if on pal editor panel, refresh all translated texts (except for hardcoded ui)
            if (session.editorOpen) {
                // Only the roster currently being viewed is refreshed eagerly. Every
                // other cached list is dropped instead, so it is re-read in the new
                // language the next time it is shown.
                const activeRoster = rosters.activeRosterKey;
                rosters.invalidateAllExcept(activeRoster);
                try {
                    if (activeRoster) await rosters.loadRosterPals(activeRoster);
                    if (pals.selectedRecordKey) await pals.loadDetail(pals.selectedRecordKey);
                    // Storage names carry the game's own words for the Global
                    // Palbox and the Dimensional Pal Storage, which the backend
                    // answers in the language it was just told about.
                    await storages.load();
                } catch (error) {
                    reportStartupFailure(error);
                    return false;
                }
                refreshSucceeded = await fetchStaticData();
                if (refreshSucceeded && research.research.Guilds?.length) {
                    refreshSucceeded = await research.load();
                }
            }
        }
        return refreshSucceeded;
    }

    // The catalogs are what this answers with; reporting the failure is what
    // stays here.
    async function fetchStaticData() {
        try {
            await catalogs.load();
            return true;
        } catch (error) {
            reportStartupFailure(error);
            return false;
        }
    }

    function reset(updateAppState = true) {
        rosters.clear();
        pals.clear();
        players.clear();

        templates.clear();
        storages.clear();
        research.clear();

        if (updateAppState) {
            session.appState = IS_LOCKED.value ? "auth-required" : "entry";
        }
    }

    // The components' way in (AGENTS.md), which is why it stays on this store
    // rather than moving with the message queue that also needs it.
    function getTranslatedText(translationKey, args = []) {
        return translate(app.locale, translationKey, args);
    }

    // ---- loading -------------------------------------------------------------

    async function loadSaveData() {
        try {
            if (!await rosters.loadRosters()) return false;
            if (!await players.loadPlayers()) return false;
            if (!await storages.load()) return false;
        } catch (error) {
            reportStartupFailure(error);
            return false;
        }

        if (!players.players.length && !HAS_WORKING_PAL_FLAG.value) {
            showToast("Message_No_Player");
        }
        return true;
    }

    async function sorryandfuckyou() {
        if (CN_WARNING_ON_LOAD.value) {
            showMessage({
                severity: "warning",
                presentation: "dialog",
                messageKey: "Message_AntiScam",
            });
            CN_WARNING_ON_LOAD.value = false;
        }
    }

    async function loadSave() {
        try {
            await session.loadSave(session.savePath);
        } catch (error) {
            reportStartupFailure(error);
            return;
        }
        // Only a save that opened is worth offering again next launch.
        if (await hydrateLoadedSave()) {
            session.rememberSavePath(localStorage, BACKEND_ORIGIN.value);
        }
    }

    async function hydrateLoadedSave() {
        reset(false);
        if (!await updateI18n()) return false;
        if (!await loadSaveData()) return false;
        if (!await fetchStaticData()) return false;
        const firstPlayer = rosters.rosters.find(roster => roster.kind === "player");
        const defaultRoster = rosters.hasBaseRoster
            ? BASE_ROSTER_KEY
            : firstPlayer?.rosterKey
                ?? (HAS_WORKING_PAL_FLAG.value ? BASE_ROSTER_KEY : undefined);
        if (defaultRoster !== undefined) await rosters.selectRoster(defaultRoster);
        IS_LOCKED.value = false;
        session.appState = "editor";
        return true;
    }

    async function writeSave() {
        let savedTo;
        try {
            savedTo = await session.writeSave();
        } catch (error) {
            reportSaveFailure(error);
            return false;
        }
        // The markers clear before the interaction gate is released, so
        // the list never redraws showing edits that are already on disk.
        pals.clearChangeStates();
        showToast("Message_Save_Success", "success", [savedTo]);
        return true;
    }

    // The one failure whose message has to carry a path. A save that could not
    // put the target back left the user's save half written, and the backup
    // folder is the only complete copy of it there is -- an error code alone does
    // not tell anyone to go and get it.
    function reportSaveFailure(error) {
        if (error.code === "SAVE_FAILED" && error.details?.restored === false) {
            showMessage({
                severity: "error",
                presentation: "dialog",
                messageKey: "Message_Save_Not_Restored",
                args: [error.details.backupPath],
                code: error.code,
                log: error.message,
            });
            return;
        }
        reportApiFailure(error, "Operation_Save");
    }

    // The prompt is dismissed per language, so the answer arrives with the app
    // config and is refreshed whenever the language changes.
    async function shownDonate() {
        try {
            await app.dismissDonationPrompt();
        } catch (error) {
            reportApiFailure(error, "Operation_Donation");
        }
    }

    return {
        SHOW_DONATE_FLAG,
        HAS_WORKING_PAL_FLAG,

        getTranslatedText,
        reset,

        ...gated(session, {
            auth,
            bootstrap,
            browseParentPath,
            browseSavePath,
            connectBackend,
            loadLatestRelease,
            loadSave,
            openFilePicker,
            shownDonate,
            unlock,
            updateI18n,
            writeSave,
        }),
    };
});
