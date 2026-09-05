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
import { useSessionStore } from "./session.js";
import { useStoragesStore } from "./storages.js";
import { useTemplatesStore } from "./templates.js";

export const usePalEditorStore = defineStore("paleditor", () => {
    // The app shell. Messages, auth, the backend connection, the static catalogs,
    // templates and the choreography around the writes -- which list to open, which Pal to select, what to say when one
    // fails. The save itself lives in `stores/session`, and its Pals, players,
    // rosters and storages in the stores below -- this store reads them, and
    // nothing reads back into it.
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

    // Every operation the UI can start holds the interaction gate for
    // as long as it runs, so nothing can begin a second one or edit what the
    // first is about to send. Applied once, to the whole surface -- the old code
    // asked each function to remember to raise and lower a flag, and the ones
    // that returned early down some branch simply left it raised.
    const gated = actions => Object.fromEntries(
        Object.entries(actions).map(([name, action]) => [
            name,
            (...args) => session.runOperation(() => action(...args)),
        ]),
    );

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
        backendAssetUrl,
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
    const {
        MESSAGE_QUEUE,
        CURRENT_MESSAGE,
    } = storeToRefs(messages);
    const {
        getMessageText,
        showMessage,
        showToast,
        confirmMessage,
        dismissMessage,
        respondToMessage,
        reportOperationError,
        reportFrontendError,
    } = messages;

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
        if (defaultRoster !== undefined) await selectPlayer(defaultRoster);
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

    // ---- selection -----------------------------------------------------------

    async function selectPlayer(rosterKey) {
        try {
            if (!await rosters.selectRoster(rosterKey)) return false;
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Pals");
            return false;
        }
        if (rosterKey === BASE_ROSTER_KEY) await research.load();
        return true;
    }

    // ---- Pal creation, deletion and transfer ---------------------------------

    // The row the list would land on once the current one is gone: the next Pal
    // the filters still show, or the first if there is none after it.
    function nextVisibleRecordKey(recordKey) {
        const visible = rosters.activeRecordKeys.filter(
            key => rosters.matchesSearch(pals.summary(key)),
        );
        const index = visible.indexOf(recordKey);
        return visible.find((key, position) => position > index && key !== recordKey)
            ?? visible.find(key => key !== recordKey)
            ?? null;
    }

    async function delPal() {
        const recordKey = pals.selectedRecordKey;
        const successor = nextVisibleRecordKey(recordKey);
        try {
            await pals.remove(recordKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Delete_Pal");
            return false;
        }
        if (successor && pals.summary(successor)) await pals.select(successor);
        return true;
    }

    // Which targets the move dialog may offer for the Pal on screen. One request
    // per target, for the group being looked at: whether a Pal may go somewhere
    // is the backend's answer about that pair, not something a storage or a
    // storage kind can be asked on its own.
    async function loadMoveTargets(storageKeys) {
        try {
            return await storages.loadCapabilities(pals.selectedRecordKey, storageKeys);
        } catch (error) {
            reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
    }

    // Every transfer ends the same way: the lists the reply named are already
    // refreshed, so what is left is opening the list the Pal is now in and
    // showing it there.
    async function followTransfer(result, rosterKey) {
        if (rosterKey !== rosters.activeRosterKey && !await selectPlayer(rosterKey)) {
            return false;
        }
        return pals.select(result.resultRecord.recordKey);
    }

    async function movePal(targetStorageKey) {
        // Read before the move: this is the answer the user was shown, and it
        // names the list the Pal is about to be in.
        const capability = storages.capability(targetStorageKey);
        let result;
        try {
            result = await storages.movePal(targetStorageKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
        // The backend answered with a question rather than a result: the dialog
        // is now showing which existing Pal an overwrite would land on.
        if (result === null) return false;
        await followTransfer(result, capability.resultRosterKey);
        showToast("Message_Pal_Moved", "success");
        return true;
    }

    async function updateConflictingPal() {
        if (!storages.conflictTarget) return false;
        const capability = storages.capability(storages.conflict.targetStorageKey);
        let result;
        try {
            result = await storages.overwriteConflictTarget();
        } catch (error) {
            reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
        if (result === null) return false;
        await followTransfer(result, capability.resultRosterKey);
        showToast("Message_Pal_Updated", "success");
        return true;
    }

    // Go and look at the Pal that is in the way instead of overwriting it. For an
    // overwrite the capability's result roster is the destination's, which is
    // exactly the list that Pal is sitting in.
    async function jumpToConflictingPal() {
        const target = storages.conflictTarget;
        if (!target) return false;
        const { resultRosterKey } = storages.capability(
            storages.conflict.targetStorageKey,
        );
        storages.clearConflict();
        if (resultRosterKey !== rosters.activeRosterKey
            && !await selectPlayer(resultRosterKey)) return false;
        return pals.select(target.recordKey);
    }

    // Which storages the add dialog may offer, for the list that is open. The
    // answer is the save's, so a target that would put the new Pal in a list
    // nobody opened is never on screen.
    async function loadCreationTargets() {
        try {
            return await storages.creationTargets(rosters.activeRosterKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Add_Pal");
            return [];
        }
    }

    // The add dialog's three tabs are one operation with three sources: a
    // default Pal, a saved template, or a record pasted in as JSON. Where it
    // lands and who owns it are the same question whichever tab is open, so only
    // `source` differs and the target storage builds the native record.
    async function addPal({
        mode = "default", templateId, palJson, targetStorageKey,
    } = {}) {
        let source;
        if (mode === "template") {
            source = { kind: "template", templateId };
        } else if (mode === "json") {
            try {
                source = { kind: "native-record", record: JSON.parse(palJson) };
            } catch (error) {
                // Text that is not JSON never reaches the backend, so there is no
                // reply for it to fail with; this says so in the dialog the same
                // way a refused record would.
                showMessage({
                    severity: "error",
                    presentation: "dialog",
                    messageKey: "Message_Operation_Failed",
                    args: [{ translationKey: "Operation_Add_Pal" }],
                    code: "PAL_JSON_INVALID",
                    log: error.message,
                });
                return false;
            }
        } else {
            source = { kind: "default" };
        }

        let result;
        try {
            result = await pals.create(
                targetStorageKey, source, rosters.activePlayerUid,
            );
        } catch (error) {
            reportApiFailure(error, "Operation_Add_Pal");
            return false;
        }
        // Which list the new Pal turned up in is the reply's answer, not a guess
        // from the target container's kind and owner.
        const [targetRoster] = result.affectedRosterKeys;
        if (targetRoster && targetRoster !== rosters.activeRosterKey) {
            await selectPlayer(targetRoster);
        }
        await pals.select(result.resultRecord.recordKey);
        return true;
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

        IS_LOCKED,

        BACKEND_ERROR,
        BACKEND_ORIGIN,
        BACKEND_CANDIDATE,
        BACKEND_RECENT,
        BACKEND_CONNECTED,
        AUTH_MESSAGE_KEY,
        MESSAGE_QUEUE,
        CURRENT_MESSAGE,


        getTranslatedText,
        getMessageText,


        reset,

        backendAssetUrl,
        requireAuth,
        clearBackendError,
        showMessage,
        dismissMessage,
        confirmMessage,
        respondToMessage,
        reportOperationError,
        reportFrontendError,

        ...gated({
            addPal,
            auth,
            bootstrap,
            browseParentPath,
            browseSavePath,
            connectBackend,
            delPal,
            jumpToConflictingPal,
            loadCreationTargets,
            loadLatestRelease,
            loadMoveTargets,
            loadSave,
            movePal,
            openFilePicker,
            selectPlayer,
            shownDonate,
            unlock,
            updateConflictingPal,
            updateI18n,
            writeSave,
        }),
    };
});
