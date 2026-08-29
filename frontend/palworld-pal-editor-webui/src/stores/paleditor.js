import { ref, computed, watch } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import {
    backendStorageKey,
    backendUrl,
    normalizeBackendOrigin,
    readRecentBackends,
    readStorage,
    rememberBackend,
    removeStorage,
    versionedBackendAssetUrl,
    writeStorage,
} from "../services/backend-connection.js";
import {
    DEFAULT_UI_TRANSLATION,
    GAME_LANGUAGES,
    UI_TRANSLATIONS,
} from "../i18n/index.js";
import { setBackendContext } from "../api/http.js";
import { usePalsStore } from "./pals.js";
import { usePlayersStore } from "./players.js";
import {
    BASE_ROSTER_KEY,
    GLOBAL_PALBOX_ROSTER_KEY,
    legacyRosterId,
    playerRosterKey,
    useRostersStore,
} from "./rosters.js";
import { useSessionStore } from "./session.js";

export const backendErrorDetails = error => {
    const status = error?.response?.status;
    if (status >= 500) {
        const payload = error.response.data;
        const details = payload?.data?.error;
        return {
            kind: "application",
            message: payload?.msg || `${error.response.statusText || "HTTP"}: ${status}`,
            code: details?.code || `HTTP ${status}`,
            log: details?.log,
        };
    }
    if (!error?.response && error?.request) {
        return { kind: "connection", message: error.message || "Network Error" };
    }
    return null;
};

export function isSkillAssignable(skill = {}, isHuman = false) {
    if (skill.Disabled) return false;
    return isHuman
        ? skill.AssignableToHumans === true
        : skill.Assignable !== false;
}

export function skillBadges(skill = {}, isHuman = false) {
    return [
        skill.NonInheritable && "nonInheritable",
        skill.Exclusive && "exclusive",
        skill.BossSkill && "boss",
        (skill.HasSkillFruit || skill.SkillFruit) && "fruit",
        !isSkillAssignable(skill, isHuman) && "disabled",
    ].filter(Boolean);
}

export function filterSkillOptions(skills, currentIds, hideInvalid, isHuman = false) {
    const rows = Array.isArray(skills) ? skills : [];
    if (!hideInvalid) return rows.slice();

    const retainedIds = new Set(currentIds ?? []);
    return rows.filter(
        skill => (
            (!skill?.Invalid && isSkillAssignable(skill, isHuman))
            || retainedIds.has(skill?.InternalName)
        ),
    );
}

export const canToggleBossVariant = pal => Boolean(
    pal?.HasBaseVariant && pal?.HasBossVariant,
);

export const maximumSuitabilities = (minimums, max) => Object.fromEntries(
    Object.entries(minimums ?? {})
        .filter(([, level]) => level > 0)
        .map(([name]) => [name, max]),
);

export function filterPalSkins(skins, selectedPal, hideInvalid = false) {
    const target = selectedPal?.FamilyID
        || selectedPal?.DataAccessKey
        || selectedPal?.CharacterID;
    return (skins ?? []).filter(skin =>
        skin?.TargetPalName === target
        && (!hideInvalid
            || !skin.Invalid
            || skin.SkinName === selectedPal?.SkinName)
    );
}

const SKILL_BADGE_TRANSLATION_KEYS = Object.freeze({
    nonInheritable: "Editor_Skill_Badge_NonInheritable",
    exclusive: "Editor_Skill_Badge_Exclusive",
    boss: "Editor_Skill_Badge_Boss",
    fruit: "Editor_Skill_Badge_Fruit",
    disabled: "Editor_Skill_Badge_Disabled",
});

const ELEMENT_ALIASES = Object.freeze({
    Leaf: "Grass",
    Earth: "Ground",
    Electricity: "Electric",
    Normal: "Neutral",
});
const ELEMENT_ICON_KEYS = new Set([
    "Water", "Fire", "Dragon", "Grass", "Ground", "Ice", "Electric", "Neutral", "Dark",
]);

export function elementIconKey(element) {
    const key = ELEMENT_ALIASES[element] ?? element;
    return ELEMENT_ICON_KEYS.has(key) ? key : null;
}

export function passiveTier(rating) {
    if (rating >= 5) return "top";
    if (rating >= 4) return "high";
    if (rating >= 2) return "positive";
    if (rating < 0) return "negative";
    return "neutral";
}

export const skillBadgeTranslationKey = badge => SKILL_BADGE_TRANSLATION_KEYS[badge];

export function genderKey(gender) {
    if (gender === "EPalGenderType::Female") return "female";
    if (gender === "EPalGenderType::Male") return "male";
    return null;
}

export function specialTypeKeys(pal = {}) {
    return [
        pal.IsTower && "tower",
        pal.IsBOSS && "boss",
        pal.IsRarePal && "rare",
        pal.IsRAID && "raid",
        pal.IsPREDATOR && "predator",
        pal.IsOilrig && "oilrig",
    ].filter(Boolean);
}

export const usePalEditorStore = defineStore("paleditor", () => {
    // What is left here after S1c: the app shell. Messages, auth, the backend
    // connection, the static catalogs, templates, containers and the write
    // operations that still speak the pre-REST routes. The save itself lives in
    // `stores/session`, and its Pals, players and rosters in the three stores
    // below -- this store reads them, and nothing reads back into it.
    const session = useSessionStore();
    const pals = usePalsStore();
    const players = usePlayersStore();
    const rosters = useRostersStore();

    // Spec §8.8: every operation the UI can start holds the interaction gate for
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

    const MAX_LEVEL = 80;
    const MAX_FRIENDSHIP_LEVEL = 10;
    const MAX_INVALID_LEVEL = 100;
    const MAX_SOULS_LEVEL = 20;
    const MAX_SUITABILITY_LEVEL = 10;

    const TECH_LV_DICT = ref({});
    const BASE_CAMP_RESEARCH = ref({ CategoryOrder: [], Guilds: [] });
    const SELECTED_RESEARCH_GUILD_ID = ref(null);
    const PASSIVE_SKILLS = ref({});
    const PASSIVE_SKILLS_LIST = ref([]);
    const ACTIVE_SKILLS = ref({});
    const ACTIVE_SKILLS_LIST = ref([]);
    const PAL_STATIC_DATA = ref({});
    const PAL_STATIC_DATA_LIST = ref([]);
    const ITEM_STATIC_DATA = ref({});
    const ITEM_STATIC_DATA_LIST = ref([]);
    const SKIN_DATA_LIST = ref([]);
    const PAL_TEMPLATES = ref([]);
    const SKILL_TEMPLATES = ref([]);
    const PAL_CONTAINERS = ref([]);
    const PAL_TRANSFER_CONFLICT = ref(null);
    const I18nList = ref(GAME_LANGUAGES);

    // flags
    const SHOW_DONATE_FLAG = ref(false);
    const UPDATE_PAL_RESELECT_CTR = ref(0);
    const HIDE_INVALID_OPTIONS = ref(true);
    const PAL_SAVE_DETAILS_OPEN = ref(false);
    const IS_PAL_SAVE_PATH = ref(false);

    // A base camp is worth listing even when nobody works in it yet, so the base
    // roster button follows the containers as well as the roster listing.
    const HAS_WORKING_PAL_FLAG = computed(() => rosters.hasBaseRoster
        || PAL_CONTAINERS.value.some(container => container.ContainerKind === "base"));

    const PAL_PASSIVE_SELECTED_ITEM = ref("");
    const PAL_ACTIVE_SELECTED_ITEM = ref("");

    // Configs
    const VERSION = ref("0.0.0");
    const UPDATE_DATA = ref({});
    const IS_OFFICIAL_BUILD = ref(false);
    const savedI18n = localStorage.getItem("PAL_I18n");
    const I18n = ref(GAME_LANGUAGES[savedI18n] ? savedI18n : "en");
    const BACKEND_ORIGIN_KEY = "PAL_BACKEND_ORIGIN";
    const normalizeStoredBackendOrigin = origin => {
        try { return normalizeBackendOrigin(origin || "", window.location.origin); }
        catch { return ""; }
    };
    const savedBackendOrigin = readStorage(localStorage, BACKEND_ORIGIN_KEY) || "";
    const initialBackendOrigin = normalizeStoredBackendOrigin(savedBackendOrigin);
    if (savedBackendOrigin !== initialBackendOrigin) {
        writeStorage(localStorage, BACKEND_ORIGIN_KEY, initialBackendOrigin);
    }
    const BACKEND_ORIGIN = ref(initialBackendOrigin);
    const BACKEND_CANDIDATE = ref(BACKEND_ORIGIN.value);
    const BACKEND_REQUEST_ORIGIN = ref(BACKEND_ORIGIN.value);
    const BACKEND_RECENT = ref(readRecentBackends(localStorage));
    const BACKEND_CONNECTED = ref(false);
    const backendAssetUrl = path => versionedBackendAssetUrl(BACKEND_ORIGIN.value, path, VERSION.value);
    const storageKey = name => backendStorageKey(name, BACKEND_ORIGIN.value);
    const HAS_PASSWORD = ref(false);
    const PATH_CONTEXT = ref(new Map());

    const SHOW_FILE_PICKER = ref(false);
    const PAL_FILE_PICKER_PATH = ref(session.recallSavePath(localStorage, BACKEND_ORIGIN.value));

    const CN_WARNING_ON_LOAD = ref(true);

    // auth
    let auth_token = readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "";

    // The API client holds the token and the origin so no call site has to pass
    // them. They change here, so they are published from here.
    function setAuthToken(token) {
        auth_token = token;
        setBackendContext({ token });
    }
    setBackendContext({ origin: BACKEND_REQUEST_ORIGIN.value, token: auth_token });
    watch(BACKEND_REQUEST_ORIGIN, origin => setBackendContext({ origin }));
    let configuredSavePath = "";
    const IS_LOCKED = ref(true);
    const BACKEND_ERROR = ref(null);
    const AUTH_MESSAGE_KEY = ref("");
    const MESSAGE_QUEUE = ref([]);
    const CURRENT_MESSAGE = computed(() => MESSAGE_QUEUE.value[0] ?? null);
    let nextMessageId = 1;

    function showMessage(message) {
        const entry = { id: nextMessageId++, args: [], ...message };
        if (entry.presentation == "dialog") {
            const firstToast = MESSAGE_QUEUE.value.findIndex(
                item => item.presentation == "toast"
            );
            MESSAGE_QUEUE.value.splice(
                firstToast < 0 ? MESSAGE_QUEUE.value.length : firstToast,
                0,
                entry
            );
        } else {
            MESSAGE_QUEUE.value.push(entry);
        }
        return entry.id;
    }

    function showToast(messageKey, severity = "warning", args = []) {
        return showMessage({ severity, presentation: "toast", messageKey, args });
    }

    function confirmMessage(messageKey, args = []) {
        return new Promise(resolve => {
            showMessage({
                severity: "warning",
                presentation: "dialog",
                messageKey,
                args,
                confirmation: true,
                resolve,
            });
        });
    }

    function dismissMessage(id) {
        const index = MESSAGE_QUEUE.value.findIndex(message => message.id == id);
        if (index < 0) return;
        const [message] = MESSAGE_QUEUE.value.splice(index, 1);
        if (message.confirmation) message.resolve(false);
    }

    function respondToMessage(id, confirmed) {
        const index = MESSAGE_QUEUE.value.findIndex(message => message.id == id);
        if (index < 0) return;
        const [message] = MESSAGE_QUEUE.value.splice(index, 1);
        if (message.confirmation) message.resolve(confirmed);
    }

    function getMessageText(message) {
        if (message?.message) return message.message;
        const args = (message?.args || []).map(arg =>
            arg?.translationKey ? getTranslatedText(arg.translationKey) : arg
        );
        return getTranslatedText(message?.messageKey, args);
    }

    function reportOperationError(operationKey, response) {
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Operation_Failed",
            args: [{ translationKey: operationKey }],
            code: response?.data?.error?.code || operationKey,
            log: response?.data?.error?.log || response?.msg,
        });
    }

    function reportFrontendError(error, context = "Frontend") {
        const exception = error instanceof Error ? error : new Error(String(error));
        console.error(context, exception);
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Unexpected_Frontend_Error",
            args: [context],
            code: exception.name,
            log: exception.stack || exception.message,
        });
    }

    // Every REST caller reports failures through here, so a refused token, a
    // backend that cannot be reached and a business error keep behaving the way
    // they always have without each caller deciding that again.
    function reportApiFailure(error, operationKey) {
        if (error.isAborted) return;
        if (error.isAuthFailure) {
            requireAuth("AuthView_Session_Expired");
            return;
        }
        if (error.isConnectionFailure) {
            BACKEND_CONNECTED.value = false;
            setBackendError({ kind: "connection", message: error.message });
            return;
        }
        // The request was never sent, so this is our bug and is reported with the
        // stack that shows where it is.
        if (error.isFrontendFault) {
            reportFrontendError(error.cause ?? error, getTranslatedText(operationKey));
            return;
        }
        showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Operation_Failed",
            args: [{ translationKey: operationKey }],
            code: error.code,
            log: error.details?.traceback || error.message,
        });
    }

    // A read that fails while the save is being opened is a failure to start, so
    // it belongs on the backend error screen rather than in a toast over an app
    // that never finished loading.
    function reportStartupFailure(error) {
        if (error.isAborted) return;
        if (error.isAuthFailure) requireAuth("AuthView_Session_Expired");
        else setBackendError(getTranslatedText("BackendError_Request_Failed", [error.message]));
    }

    function setBackendError(error) {
        BACKEND_ERROR.value = typeof error === "string"
            ? { kind: "application", message: error }
            : error;
        if (session.appState === "connecting") session.appState = "backend-error";
    }

    function handleRequestError(error, method) {
        const backendError = backendErrorDetails(error);
        if (backendError) {
            if (backendError.kind === "connection") BACKEND_CONNECTED.value = false;
            setBackendError(backendError);
            console.error(`${method}(): ${backendError.message}`);
            return false;
        }
        if (error.response) {
            const message = `${error.response.statusText}: ${error.response.status}`;
            console.log(message);
            return typeof error.response.data === "object"
                ? error.response.data
                : { msg: message };
        }
        reportFrontendError(error, method);
        return false;
    }

    async function GET(api) {
        try {
            const response = await axios.get(backendUrl(BACKEND_REQUEST_ORIGIN.value, api), {
                headers: {
                    Authorization: "Bearer " + auth_token,
                },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "get");
        }
    }

    async function POST(api, data) {
        try {
            const response = await axios.post(backendUrl(BACKEND_REQUEST_ORIGIN.value, api), data, {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "post");
        }
    }

    async function PATCH(api, data) {
        try {
            const response = await axios.patch(backendUrl(BACKEND_REQUEST_ORIGIN.value, api), data, {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "patch");
        }
    }

    async function DELETE(api) {
        try {
            const response = await axios.delete(backendUrl(BACKEND_REQUEST_ORIGIN.value, api), {
                headers: { Authorization: "Bearer " + auth_token },
            });

            return response.data;
        } catch (error) {
            return handleRequestError(error, "delete");
        }
    }

    async function auth() {
        const response = await GET("/api/auth/auth");
        if (response === false) return false;

        if (response.status == 0) {
            IS_LOCKED.value = false;
            return true;
        }
        requireAuth("AuthView_Session_Expired");
        return false;
    }

    function clearBackendError() {
        BACKEND_ERROR.value = null;
    }

    function requireAuth(messageKey = "") {
        setAuthToken("");
        removeStorage(localStorage, storageKey("PAL_AUTH_TOKEN"));
        AUTH_MESSAGE_KEY.value = messageKey;
        IS_LOCKED.value = true;
        session.appState = "auth-required";
    }

    async function unlock(password, remember = false) {
        AUTH_MESSAGE_KEY.value = "";
        session.appState = "connecting";
        const response = await POST("/api/auth/login", {
            password,
            remember,
        });
        if (response === false) return false;

        if (response.status == 0) {
            IS_LOCKED.value = false;
            setAuthToken(response.data.access_token);
            if (remember) {
                writeStorage(localStorage, storageKey("PAL_AUTH_TOKEN"), auth_token);
            } else {
                removeStorage(localStorage, storageKey("PAL_AUTH_TOKEN"));
            }
            session.appState = "connecting";
            return await resumeBackendSave();
        } else if (response.status == 2) {
            requireAuth("AuthView_Wrong_Password");
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }
        return false;
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
            PAL_TEMPLATES.value = [];
            SKILL_TEMPLATES.value = [];
            setAuthToken(readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");
            PAL_FILE_PICKER_PATH.value = session.recallSavePath(localStorage, origin);
        }
    }

    async function fetch_config(origin = BACKEND_REQUEST_ORIGIN.value) {

        const response = await GET("/api/save/fetch_config");
        if (response === false) return false;

        if (response.status == 0) {
            promoteBackend(origin);
            BACKEND_CONNECTED.value = true;
            if (response.data.I18nList) {
                I18nList.value = response.data.I18nList;
            }
            if (!localStorage.getItem("PAL_I18n") && I18nList.value[response.data.I18n]) {
                I18n.value = response.data.I18n;
            }
            if (!session.savePath) {
                session.savePath = response.data.Path;
            }
            configuredSavePath = response.data.Path;
            HAS_PASSWORD.value = response.data.HasPassword;
            VERSION.value = response.data.VERSION;
            IS_OFFICIAL_BUILD.value = response.data.IsOfficialBuild;
        } else if (response.status == 2) {
            if (origin === BACKEND_ORIGIN.value) requireAuth();
            else setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }

        return response.status == 0;
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
            if (configuredSavePath) {
                session.savePath = configuredSavePath;
                session.writeBackPath = configuredSavePath;
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
        else setAuthToken(auth_token || readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");

        if (!await fetch_config(BACKEND_CANDIDATE.value)) {
            BACKEND_REQUEST_ORIGIN.value = BACKEND_ORIGIN.value;
            return false;
        }
        if (HAS_PASSWORD.value) {
            if (!auth_token) {
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
        const previousToken = auth_token;
        const wasConnected = BACKEND_CONNECTED.value;
        candidate = normalizeBackendOrigin(candidate, window.location.origin);
        try {
            const probe = await axios.get(backendUrl(candidate, "/api/save/fetch_config"), { timeout: 5000 });
            if (probe.data?.status !== 0) {
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
            auth_token = previousToken;
            BACKEND_CANDIDATE.value = previousOrigin;
            BACKEND_REQUEST_ORIGIN.value = previousOrigin;
            BACKEND_CONNECTED.value = wasConnected;
        }
        return BACKEND_ORIGIN.value === candidate;
    }

    async function get_updates() {
        const response = await GET("/api/save/update");
        if (response === false) return;

        if (response.status == 0) {
            return UPDATE_DATA.value = response.data;
        }
    }

    function update_path_picker_result(data) {
        IS_PAL_SAVE_PATH.value = data.isPalDir;
        PAL_FILE_PICKER_PATH.value = data.currentPath;
        PATH_CONTEXT.value = new Map(Object.entries(data.children));
        SHOW_FILE_PICKER.value = true;
    }

    async function show_file_picker() {

        let response = undefined;
        if (session.savePath) {
            response = await POST("/api/save/path", {
                path: session.savePath,
            });
            if (response === false) return;
            if (response.status != 0) {
                session.forgetSavePath(localStorage, BACKEND_ORIGIN.value);
                response = await GET("/api/save/path");
            }
        } else {
            response = await GET("/api/save/path");
        }

        if (response === false) return false;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

    }

    async function path_back() {

        const response = await PATCH("/api/save/path");

        if (response === false) return;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

    }

    async function update_picker_result(path) {

        const response = await POST("/api/save/path", {
            path: path,
        });

        if (response === false) return;

        if (response.status == 0) {
            update_path_picker_result(response.data);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Select_Path", response);
        }

    }

    async function updateI18n() {
        localStorage.setItem("PAL_I18n", I18n.value);
        if (IS_LOCKED.value || BACKEND_ERROR.value) return true;

        sorryandfuckyou();

        const response = await PATCH("/api/save/i18n", { I18n: I18n.value });
        if (response === false) {
            return false;
        }

        let refreshSucceeded = response.status == 0;
        if (response.status == 0) {
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
                } catch (error) {
                    reportStartupFailure(error);
                    return false;
                }
                refreshSucceeded = await fetchStaticData();
                if (refreshSucceeded && BASE_CAMP_RESEARCH.value.Guilds?.length) {
                    refreshSucceeded = await fetchBaseCampResearch();
                }
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [response.msg]));
        }
        return response.status == 0 && refreshSucceeded;
    }

    async function fetchStaticData() {
        const passive_skills_raw = await GET("/api/save/passive_skills");
        if (passive_skills_raw === false) return false;

        if (passive_skills_raw.status == 0) {
            PASSIVE_SKILLS.value = passive_skills_raw.data.dict;
            PASSIVE_SKILLS_LIST.value = passive_skills_raw.data.arr;
        } else if (passive_skills_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [passive_skills_raw.msg]));
            return false;
        }

        const active_skills_raw = await GET("/api/save/active_skills");
        if (active_skills_raw === false) return false;

        if (active_skills_raw.status == 0) {
            ACTIVE_SKILLS.value = active_skills_raw.data.dict;
            ACTIVE_SKILLS_LIST.value = active_skills_raw.data.arr;
        } else if (active_skills_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [active_skills_raw.msg]));
            return false;
        }

        const pal_data_raw = await GET("/api/save/pal_data");
        if (pal_data_raw === false) return false;

        if (pal_data_raw.status == 0) {
            PAL_STATIC_DATA.value = pal_data_raw.data.dict;
            PAL_STATIC_DATA_LIST.value = pal_data_raw.data.arr;
        } else if (pal_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [pal_data_raw.msg]));
            return false;
        }

        const item_data_raw = await GET("/api/save/item_data");
        if (item_data_raw === false) return false;
        if (item_data_raw.status == 0) {
            ITEM_STATIC_DATA.value = item_data_raw.data.dict;
            ITEM_STATIC_DATA_LIST.value = item_data_raw.data.arr;
        } else if (item_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [item_data_raw.msg]));
            return false;
        }

        const tech_data_raw = await GET("/api/save/tech_data");
        if (tech_data_raw === false) return false;

        if (tech_data_raw.status == 0) {
            TECH_LV_DICT.value = tech_data_raw.data.techLvDict;
        } else if (tech_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [tech_data_raw.msg]));
            return false;
        }

        const skin_data_raw = await GET("/api/save/skin_data");
        if (skin_data_raw === false) return false;
        if (skin_data_raw.status == 0) {
            SKIN_DATA_LIST.value = skin_data_raw.data.arr;
        } else if (skin_data_raw.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        } else {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [skin_data_raw.msg]));
            return false;
        }
        return true;
    }

    function reset(updateAppState = true) {
        rosters.clear();
        pals.clear();
        players.clear();

        PAL_PASSIVE_SELECTED_ITEM.value = "";
        PAL_ACTIVE_SELECTED_ITEM.value = "";
        PAL_TEMPLATES.value = [];
        SKILL_TEMPLATES.value = [];
        PAL_CONTAINERS.value = [];
        PAL_TRANSFER_CONFLICT.value = null;
        BASE_CAMP_RESEARCH.value = { CategoryOrder: [], Guilds: [] };
        SELECTED_RESEARCH_GUILD_ID.value = null;

        if (updateAppState) {
            session.appState = IS_LOCKED.value ? "auth-required" : "entry";
        }
    }

    function getTranslatedText(translationKey, args = []) {
        let translation = UI_TRANSLATIONS[I18n.value]?.[translationKey]
            ?? DEFAULT_UI_TRANSLATION[translationKey];
        if (!translation) {
            console.warn(`Translation key "${translationKey}" not found.`);
            return "I18N_MISSING";
        }
        args.forEach((arg, index) => {
            translation = translation.replace(`{{${index}}}`, arg);
        });
        return translation;
    }

    function getTechName(internalName) {
        for (const entries of Object.values(TECH_LV_DICT.value)) {
            const tech = entries.find(item => item.InternalName === internalName);
            if (tech) return tech.I18n?.Name || tech.InternalName;
        }
        return "";
    }

    // ---- players -------------------------------------------------------------
    // `PATCH /api/players/{uid}` and the inventory sub-resources are specified in
    // §8.2 but built by no task in this plan, so these three still speak the
    // pre-REST routes and stay here rather than in `stores/players`.

    async function updatePlayer(e) {
        const key = e.target.name;
        const value = e.target.value;
        const playerUid = rosters.activePlayerUid;

        if (playerUid == null) {
            showToast("Message_Select_Player");
            return;
        }

        const response = await PATCH("/api/player/player_data", {
            key: key,
            value: value,
            PlayerUId: playerUid,
        });
        if (response === false) return;

        if (response.status == 0) {
            try {
                await players.refreshPlayer(playerUid);
            } catch (error) {
                reportApiFailure(error, "Operation_Load_Player");
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Update_Player", response);
        }
    }

    function playerLevelDown() {
        const player = players.selectedPlayer;
        if (!player || player.Level <= 1) return;
        return updatePlayer({ target: { name: "Level", value: player.Level - 1 } });
    }

    function playerLevelUp() {
        const player = players.selectedPlayer;
        const ceiling = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        if (!player || player.Level >= ceiling) return;
        return updatePlayer({ target: { name: "Level", value: player.Level + 1 } });
    }

    function playerMaxLevel() {
        const value = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        return updatePlayer({ target: { name: "Level", value } });
    }

    function setStatusPoint(name) {
        const player = players.selectedPlayer;
        if (!player) return;
        let points = Number(player.StatusPointTotals[name]);
        if (!Number.isFinite(points)) points = 0;
        points = Math.min(
            Math.max(Math.trunc(points), player.StatusPointMinimums[name] ?? 0),
            player.StatusPointTotalMaximums[name] ?? 0,
        );
        player.StatusPointTotals[name] = points;
        return updatePlayer({
            target: {
                name: player.StatusPointMetadata[name]?.category === "stat"
                    ? "set_TotalStatusPoint"
                    : "set_StatusPoint",
                value: { name, points },
            },
        });
    }

    function toggleTech(tech, status) {
        return updatePlayer({
            target: {
                name: "toggle_UnlockedRecipeTechnologyNames",
                value: { tech, status },
            },
        });
    }

    async function loadPlayerInventory() {
        const playerUid = rosters.activePlayerUid;
        if (!playerUid) return false;
        const response = await POST("/api/player/inventory", {
            PlayerUId: playerUid,
        });
        if (response === false) return false;
        if (response.status == 0) {
            players.inventory = response.data;
            return true;
        }
        if (response.status == 2) requireAuth("AuthView_Session_Expired");
        else reportOperationError("Operation_Load_Player_Data", response);
        return false;
    }

    async function patchInventorySlot(containerKind, slotIndex, itemId, count) {
        const playerUid = rosters.activePlayerUid;
        if (!playerUid) return false;
        const response = await PATCH("/api/player/inventory_slot", {
            PlayerUId: playerUid,
            ContainerKind: containerKind,
            SlotIndex: slotIndex,
            ItemId: itemId,
            Count: count,
            AllowOverstack: !HIDE_INVALID_OPTIONS.value,
        });
        if (response !== false && response.status == 0) {
            await loadPlayerInventory();
            return true;
        }
        if (response?.status == 2) requireAuth("AuthView_Session_Expired");
        else if (response !== false) reportOperationError("Operation_Update_Player", response);
        return false;
    }

    // ---- loading -------------------------------------------------------------

    async function loadSaveData() {
        try {
            if (!await rosters.loadRosters()) return false;
            if (!await players.loadPlayers()) return false;
        } catch (error) {
            reportStartupFailure(error);
            return false;
        }

        // Containers are still the pre-REST registry; `GET /api/storages` and
        // `stores/storages` are S4's.
        const containers = await GET("/api/pal/containers");
        if (containers === false) return false;
        if (containers.status == 2) {
            requireAuth("AuthView_Session_Expired");
            return false;
        }
        if (containers.status != 0) {
            setBackendError(getTranslatedText("BackendError_Request_Failed", [containers.msg]));
            return false;
        }
        PAL_CONTAINERS.value = containers.data || [];

        if (!players.players.length && !HAS_WORKING_PAL_FLAG.value) {
            showToast("Message_No_Player");
        }
        return true;
    }

    async function fetchPalContainers() {
        const response = await GET("/api/pal/containers");
        if (response === false) return false;
        if (response.status == 0) {
            PAL_CONTAINERS.value = response.data || [];
            return true;
        }
        if (response.status == 2) requireAuth("AuthView_Session_Expired");
        else reportOperationError("Operation_Load_Pals", response);
        return false;
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
        try {
            await session.writeSave();
        } catch (error) {
            reportApiFailure(error, "Operation_Save");
            return false;
        }
        showToast("Message_Save_Success", "success", [session.writeBackPath]);
        return true;
    }

    async function fetchBaseCampResearch() {
        const response = await GET("/api/save/basecamp/research");
        if (response === false) return false;
        if (response.status == 0) {
            BASE_CAMP_RESEARCH.value = response.data ?? { CategoryOrder: [], Guilds: [] };
            const guilds = BASE_CAMP_RESEARCH.value.Guilds ?? [];
            if (!guilds.some(guild => guild.GuildId === SELECTED_RESEARCH_GUILD_ID.value)) {
                SELECTED_RESEARCH_GUILD_ID.value = guilds[0]?.GuildId ?? null;
            }
            return true;
        }
        if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_BaseCamp_Research", response);
        }
        return false;
    }

    async function completeBaseCampResearch(scope) {
        const guildId = SELECTED_RESEARCH_GUILD_ID.value;
        if (!guildId) return false;
        const response = await PATCH("/api/save/basecamp/research", {
            GuildId: guildId,
            ...scope,
        });
        if (response === false) return false;
        if (response.status == 0) {
            BASE_CAMP_RESEARCH.value = response.data.Research;
            showToast("Message_BaseCamp_Research_Completed", "success", [response.data.Changed]);
            return true;
        }
        if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_BaseCamp_Research", response);
        }
        return false;
    }

    // ---- selection -----------------------------------------------------------

    async function selectPlayer(rosterKey) {
        try {
            if (!await rosters.selectRoster(rosterKey)) return false;
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Pals");
            return false;
        }
        if (rosterKey === BASE_ROSTER_KEY) await fetchBaseCampResearch();
        return true;
    }

    async function selectPal(recordKey) {
        try {
            if (await pals.select(recordKey)) return true;
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Pal");
            return false;
        }
        showToast("Message_Select_Pal_Failed");
        return false;
    }

    // ---- Pal edits -----------------------------------------------------------
    // Everything below still posts the generic `{key, value}` action to
    // `PATCH /api/pal/paldata`. S2a builds the typed replacements and S2b moves
    // these into `stores/pals` as it deletes the route.

    const updatePal = (...args) => session.runOperation(() => applyPalEdit(...args));

    async function applyPalEdit(e) {
        const key = e.target.name;
        const value = e.target.value;
        const recordKey = pals.selectedRecordKey;
        const addingActiveSkill = key === "add_MasteredWaza" || key === "add_EquipWaza";
        const activeSkill = ACTIVE_SKILLS.value[value];
        if (
            addingActiveSkill
            && (
                !activeSkill
                || (
                    HIDE_INVALID_OPTIONS.value
                    && !isSkillAssignable(activeSkill, pals.selectedPal?.IsHuman)
                )
            )
        ) {
            showToast("Message_Skill_Not_Assignable");
            return;
        }

        const response = await PATCH("/api/pal/paldata", {
            key: key,
            value: value,
            RecordKey: recordKey,
        });
        if (response === false) return;

        if (response.status == 0) {
            pals.markEdited(recordKey);
            if (recordKey) {
                await refreshPal(recordKey);
                UPDATE_PAL_RESELECT_CTR.value++;
            }
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Update_Pal", response);
        }
    }

    // A write answers in the pre-REST DTO, which spells its fields differently
    // from `PalSummary`/`PalDetail`. Rather than teach the cache two vocabularies,
    // the Pal is re-read through the resource that owns it.
    async function refreshPal(recordKey) {
        try {
            return await pals.loadDetail(recordKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Pal");
            return false;
        }
    }

    const editedPal = () => pals.selectedPal;

    function swapRare() {
        return updatePal({ target: { name: "IsRarePal", value: !editedPal().IsRarePal } });
    }

    function swapBoss() {
        return updatePal({ target: { name: "IsBOSS", value: !editedPal().IsBOSS } });
    }

    function toggleAwakening() {
        return updatePal({ target: { name: "IsAwakening", value: !editedPal().IsAwakening } });
    }

    function palLevelDown() {
        const pal = editedPal();
        if (pal.Level <= 1) return;
        return updatePal({ target: { name: "Level", value: pal.Level - 1 } });
    }

    function palLevelUp() {
        const pal = editedPal();
        const ceiling = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        if (pal.Level >= ceiling) return;
        return updatePal({ target: { name: "Level", value: pal.Level + 1 } });
    }

    function palMaxLevel() {
        const value = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        return updatePal({ target: { name: "Level", value } });
    }

    function friendshipDown() {
        const pal = editedPal();
        if (pal.FriendshipLevel <= -3) return;
        return updatePal({
            target: { name: "FriendshipLevel", value: pal.FriendshipLevel - 1 },
        });
    }

    function friendshipUp() {
        const pal = editedPal();
        if (pal.FriendshipLevel >= MAX_FRIENDSHIP_LEVEL) return;
        return updatePal({
            target: { name: "FriendshipLevel", value: pal.FriendshipLevel + 1 },
        });
    }

    function maxFriendship() {
        return updatePal({
            target: { name: "FriendshipLevel", value: MAX_FRIENDSHIP_LEVEL },
        });
    }

    function swapGender() {
        const gender = editedPal().Gender;
        let next = HIDE_INVALID_OPTIONS.value ? "NONE" : "EPalGenderType::Female";
        if (gender == "EPalGenderType::Female") next = "EPalGenderType::Male";
        if (gender == "EPalGenderType::Male") next = "EPalGenderType::Female";
        return updatePal({ target: { name: "Gender", value: next } });
    }

    function removePassiveSkill(e) {
        return updatePal({
            target: { name: "pop_PassiveSkillList", value: e.target.name },
        });
    }

    function addPassiveSkill() {
        const skill = PAL_PASSIVE_SELECTED_ITEM.value;
        if (!PASSIVE_SKILLS.value[skill]) {
            showToast("Message_Select_Skill");
            return;
        }
        if (HIDE_INVALID_OPTIONS.value && editedPal().PassiveSkillList.length >= 4) {
            showToast("Message_Passive_Limit");
            return;
        }
        return updatePal({ target: { name: "add_PassiveSkillList", value: skill } });
    }

    function removeEquipWaza(e) {
        return updatePal({ target: { name: "pop_EquipWaza", value: e.target.name } });
    }

    function addEquipWaza(e) {
        return updatePal({ target: { name: "add_EquipWaza", value: e.target.name } });
    }

    function removeMasteredWaza(e) {
        return updatePal({ target: { name: "pop_MasteredWaza", value: e.target.name } });
    }

    function addMasteredWaza() {
        const skill = PAL_ACTIVE_SELECTED_ITEM.value;
        if (!ACTIVE_SKILLS.value[skill]) {
            showToast("Message_Select_Skill");
            return;
        }
        return updatePal({ target: { name: "add_MasteredWaza", value: skill } });
    }

    function setSuitability(name, value) {
        const pal = editedPal();
        const min = pal.SuitabilityMinimums[name] || 0;
        if (HIDE_INVALID_OPTIONS.value && min == 0 && value != 0) {
            showToast("Message_Invalid_Suitability");
            return;
        }
        value = Math.min(Math.max(value, min), MAX_SUITABILITY_LEVEL);
        if (value == pal.Suitabilities[name]) return;
        return updatePal({
            target: { name: "set_Suitability", value: { name, level: value } },
        });
    }

    function suitabilityUp(e) {
        const name = e.target.name;
        return setSuitability(name, editedPal().Suitabilities[name] + 1);
    }

    function suitabilityDown(e) {
        const name = e.target.name;
        return setSuitability(name, editedPal().Suitabilities[name] - 1);
    }

    function maxSuitabilities() {
        const values = maximumSuitabilities(
            editedPal().SuitabilityMinimums,
            MAX_SUITABILITY_LEVEL,
        );
        if (!Object.keys(values).length) return;
        return updatePal({ target: { name: "set_Suitabilities", value: values } });
    }

    function changeSpecies(characterId) {
        return updatePal({ target: { name: "CharacterID", value: characterId } });
    }

    async function dumpPalData() {
        try {
            const response = await POST("/api/pal/dump_data", {
                RecordKey: pals.selectedRecordKey,
            });

            if (response === false) return;
            if (response.status == 0) {
                await navigator.clipboard.writeText(response.data);
                showToast("Message_Pal_Copied", "success");
            } else if (response.status == 2) {
                requireAuth("AuthView_Session_Expired");
            } else {
                reportOperationError("Operation_Copy_Pal", response);
            }
        } catch (error) {
            reportFrontendError(error, getTranslatedText("Operation_Copy_Pal"));
        }
    }

    async function maximizePal() {
        const recordKey = pals.selectedRecordKey;
        if (!recordKey) return false;
        try {
            const response = await POST("/api/pal/maximize", { RecordKey: recordKey });
            if (response === false) return false;
            if (response.status == 0) {
                await refreshPal(recordKey);
                pals.markEdited(recordKey);
                UPDATE_PAL_RESELECT_CTR.value++;
                showToast("Message_Pal_Maximized", "success");
                return true;
            }
            if (response.status == 2) {
                requireAuth("AuthView_Session_Expired");
            } else {
                reportOperationError("Operation_Maximize_Pal", response);
            }
            return false;
        } catch (error) {
            reportFrontendError(error, getTranslatedText("Operation_Maximize_Pal"));
            return false;
        }
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
        const response = await DELETE(`/api/pal/pal/${encodeURIComponent(recordKey)}`);

        if (response === false) return;

        if (response.status == 0) {
            pals.forget(recordKey);
            await refreshRosters([rosters.activeRosterKey]);
            if (successor && pals.summary(successor)) await selectPal(successor);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Delete_Pal", response);
        }
    }

    // Refresh only the rosters an operation touched. Everything else keeps its
    // keys and is re-read by `selectPlayer` the next time it is opened.
    async function refreshRosters(rosterKeys) {
        await fetchPalContainers();
        const affected = new Set((rosterKeys || [rosters.activeRosterKey]).filter(Boolean));
        try {
            for (const rosterKey of affected) await rosters.loadRosterPals(rosterKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Pals");
            return false;
        }
        return true;
    }

    // Which list a Pal ends up in once it reaches this container. A base camp and
    // the Global Palbox are places; everywhere else the list is a player's, and
    // which player that is depends on the operation.
    function rosterKeyForContainer(container, ownerUid) {
        if (container?.ContainerKind === "base") return BASE_ROSTER_KEY;
        if (container?.StorageKind === "global_palbox") return GLOBAL_PALBOX_ROSTER_KEY;
        return ownerUid ? playerRosterKey(ownerUid) : null;
    }

    async function movePal(targetContainerId) {
        const recordKey = pals.selectedRecordKey;
        if (!recordKey || !targetContainerId) return false;
        const pal = pals.selectedPal;
        const target = PAL_CONTAINERS.value.find(
            container => container.StorageKey === targetContainerId || container.ContainerId === targetContainerId
        );
        PAL_TRANSFER_CONFLICT.value = null;
        const response = await POST("/api/pal/transfer", {
            SourceRecordKey: recordKey,
            TargetStorageKey: target?.StorageKey || targetContainerId,
            Action: target?.StorageKind === "global_palbox" || pal?.storageKind === "global_palbox" ? "clone" : "move",
        });
        if (response === false) return false;
        if (response.status != 0) {
            if (response.status == 2) requireAuth("AuthView_Session_Expired");
            else if (response.data?.Code === "PAL_IDENTITY_CONFLICT") {
                const lockedTarget = response.data.Candidates?.find(
                    candidate => candidate.RecordKey === response.data.LockedTarget,
                );
                PAL_TRANSFER_CONFLICT.value = {
                    ...response.data,
                    SourceRecordKey: recordKey,
                    TargetStorageKey: lockedTarget?.StorageKey
                        || target?.StorageKey
                        || targetContainerId,
                };
            }
            else reportOperationError("Operation_Move_Pal", response);
            return false;
        }
        pals.markEdited(recordKey);
        const sourceRoster = rosters.activeRosterKey;
        // A DPS holds Pals its owner never owned, and the backend files those by
        // the Pal's owner, not the storage's.
        const targetRoster = rosterKeyForContainer(target, target?.StorageKind === "dps"
            ? pal?.OwnerPlayerUId
            : target?.OwnerPlayerUId);
        await refreshRosters([sourceRoster, targetRoster]);
        if (targetRoster) {
            await selectPlayer(targetRoster);
            await selectPal(response.data.RecordKey);
        }
        showToast("Message_Pal_Moved", "success");
        return true;
    }

    // The roster a conflict candidate is sitting in. Candidates come from the
    // pre-REST transfer route, so they still spell their fields its way.
    function candidateRosterKey(candidate) {
        if (!candidate) return null;
        if (candidate.StorageKind === "global_palbox") return GLOBAL_PALBOX_ROSTER_KEY;
        return candidate.OwnerPlayerUId
            ? playerRosterKey(candidate.OwnerPlayerUId)
            : BASE_ROSTER_KEY;
    }

    async function updateConflictingPal() {
        const conflict = PAL_TRANSFER_CONFLICT.value;
        if (!conflict?.LockedTarget) return false;
        const response = await POST("/api/pal/transfer", {
            SourceRecordKey: conflict.SourceRecordKey,
            TargetStorageKey: conflict.TargetStorageKey,
            Action: "update",
            ExpectedTargetRecordKey: conflict.LockedTarget,
        });
        if (response === false) return false;
        if (response.status != 0) {
            if (response.status == 2) requireAuth("AuthView_Session_Expired");
            else reportOperationError("Operation_Move_Pal", response);
            return false;
        }
        pals.markEdited(conflict.LockedTarget);
        const conflictRoster = candidateRosterKey(conflict.Candidates?.find(
            item => item.RecordKey === conflict.LockedTarget,
        ));
        PAL_TRANSFER_CONFLICT.value = null;
        await refreshRosters([rosters.activeRosterKey, conflictRoster]);
        if (conflictRoster) {
            await selectPlayer(conflictRoster);
            await selectPal(conflict.LockedTarget);
        }
        showToast("Message_Pal_Updated", "success");
        return true;
    }

    async function jumpToConflictingPal() {
        const conflict = PAL_TRANSFER_CONFLICT.value;
        const candidate = conflict?.Candidates?.find(
            item => item.RecordKey === conflict.LockedTarget,
        );
        if (!candidate) return false;
        const rosterKey = candidateRosterKey(candidate);
        PAL_TRANSFER_CONFLICT.value = null;
        await selectPlayer(rosterKey);
        await selectPal(candidate.RecordKey);
        return true;
    }

    function clearPalTransferConflict() {
        PAL_TRANSFER_CONFLICT.value = null;
    }

    async function addPal(options = {}) {
        const rosterId = legacyRosterId(rosters.activeRosterKey);
        const response = await POST("/api/pal/add_pal", {
            PlayerUId: rosterId,
            RosterKey: rosterId,
            TargetStorageKey: options.TargetStorageKey,
            ...options,
        });

        if (response === false) {
            return false;
        }

        if (response.status == 0) {
            const target = PAL_CONTAINERS.value.find(
                container => container.StorageKey === options.TargetStorageKey
            );
            const targetRoster = rosterKeyForContainer(
                target,
                target?.OwnerPlayerUId || rosters.activePlayerUid,
            );
            await refreshRosters([rosters.activeRosterKey, targetRoster]);
            if (targetRoster) await selectPlayer(targetRoster);
            await selectPal(response.data.RecordKey);
            return true;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Add_Pal", response);
        }

        return false;
    }

    async function dupePal() {
        const response = await POST("/api/pal/dupe_pal", {
            PlayerUId: legacyRosterId(rosters.activeRosterKey),
            RecordKey: pals.selectedRecordKey,
        });

        if (response === false) return;

        if (response.status == 0) {
            await refreshRosters([rosters.activeRosterKey]);
            await selectPal(response.data.RecordKey);
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Duplicate_Pal", response);
        }
    }

    // ---- templates -----------------------------------------------------------

    async function fetchPalTemplates() {
        const response = await GET("/api/pal/templates");
        if (response === false) return false;
        if (response.status == 0) {
            PAL_TEMPLATES.value = response.data || [];
            return true;
        }
        reportOperationError("Operation_Load_Pal_Templates", response);
        return false;
    }

    async function savePalTemplate(name) {
        if (!pals.selectedRecordKey) return false;
        const response = await POST("/api/pal/templates", {
            RecordKey: pals.selectedRecordKey,
            Name: name,
        });
        if (response === false) return false;
        if (response.status == 0) {
            await fetchPalTemplates();
            showToast("Message_Pal_Template_Saved", "success");
            return true;
        }
        reportOperationError("Operation_Save_Pal_Template", response);
        return false;
    }

    async function deletePalTemplate(templateId) {
        const response = await DELETE(`/api/pal/templates/${templateId}`);
        if (response === false) return false;
        if (response.status == 0) {
            PAL_TEMPLATES.value = PAL_TEMPLATES.value.filter(
                template => template.Id != templateId
            );
            showToast("Message_Pal_Template_Deleted", "success");
            return true;
        }
        reportOperationError("Operation_Delete_Pal_Template", response);
        return false;
    }

    async function fetchSkillTemplates() {
        const response = await GET("/api/pal/skill_templates");
        if (response === false) return false;
        if (response.status == 0) {
            SKILL_TEMPLATES.value = response.data || [];
            return true;
        }
        reportOperationError("Operation_Load_Skill_Templates", response);
        return false;
    }

    async function saveSkillTemplate(type, name) {
        if (!pals.selectedRecordKey) return false;
        const response = await POST("/api/pal/skill_templates", {
            RecordKey: pals.selectedRecordKey,
            Type: type,
            Name: name,
        });
        if (response === false) return false;
        if (response.status == 0) {
            SKILL_TEMPLATES.value.push(response.data);
            showToast("Message_Skill_Template_Saved", "success");
            return true;
        }
        reportOperationError("Operation_Save_Skill_Template", response);
        return false;
    }

    async function renameSkillTemplate(templateId, name) {
        const response = await PATCH(`/api/pal/skill_templates/${templateId}`, {
            Name: name,
        });
        if (response === false) return false;
        if (response.status == 0) {
            const index = SKILL_TEMPLATES.value.findIndex(
                template => template.Id == templateId
            );
            if (index >= 0) SKILL_TEMPLATES.value[index] = response.data;
            showToast("Message_Skill_Template_Renamed", "success");
            return true;
        }
        reportOperationError("Operation_Rename_Skill_Template", response);
        return false;
    }

    async function applySkillTemplate(templateId) {
        const recordKey = pals.selectedRecordKey;
        if (!recordKey) return false;
        const response = await POST(`/api/pal/skill_templates/${templateId}/apply`, {
            RecordKey: recordKey,
        });
        if (response === false) return false;
        if (response.status == 0) {
            await refreshPal(recordKey);
            pals.markEdited(recordKey);
            showToast("Message_Skill_Template_Applied", "success");
            return true;
        }
        reportOperationError("Operation_Apply_Skill_Template", response);
        return false;
    }

    async function deleteSkillTemplate(templateId) {
        const response = await DELETE(`/api/pal/skill_templates/${templateId}`);
        if (response === false) return false;
        if (response.status == 0) {
            SKILL_TEMPLATES.value = SKILL_TEMPLATES.value.filter(
                template => template.Id != templateId
            );
            showToast("Message_Skill_Template_Deleted", "success");
            return true;
        }
        reportOperationError("Operation_Delete_Skill_Template", response);
        return false;
    }

    function palElementKeys(DataAccessKey) {
        return (PAL_STATIC_DATA.value[DataAccessKey]?.Elements ?? [])
            .map(elementIconKey)
            .filter(Boolean);
    }

    async function shownDonate() {
        await PATCH("/api/save/donate");
    }

    async function showDonate() {
        const response = await GET("/api/save/donate");
        if (response === false) return;
        let res = false;
        if (response.status == 0) {
            res = response.data?.shouldShowDonate == true;
            IS_LOCKED.value = false;
        } else if (response.status == 2) {
            requireAuth("AuthView_Session_Expired");
        } else {
            reportOperationError("Operation_Donation", response);
        }
        return res;
    }

    return {
        MAX_LEVEL,
        MAX_INVALID_LEVEL,
        MAX_SOULS_LEVEL,
        MAX_SUITABILITY_LEVEL,
        MAX_FRIENDSHIP_LEVEL,

        PAL_PASSIVE_SELECTED_ITEM,
        PAL_ACTIVE_SELECTED_ITEM,
        SHOW_DONATE_FLAG,
        UPDATE_PAL_RESELECT_CTR,
        HIDE_INVALID_OPTIONS,
        PAL_SAVE_DETAILS_OPEN,
        HAS_WORKING_PAL_FLAG,

        IS_LOCKED,
        HAS_PASSWORD,
        BACKEND_ERROR,
        BACKEND_ORIGIN,
        BACKEND_CANDIDATE,
        BACKEND_RECENT,
        BACKEND_CONNECTED,
        AUTH_MESSAGE_KEY,
        MESSAGE_QUEUE,
        CURRENT_MESSAGE,

        PATH_CONTEXT,
        SHOW_FILE_PICKER,
        PAL_FILE_PICKER_PATH,
        IS_PAL_SAVE_PATH,

        VERSION,
        UPDATE_DATA,
        IS_OFFICIAL_BUILD,
        I18n,
        I18nList,
        PAL_STATIC_DATA,
        PAL_STATIC_DATA_LIST,
        ITEM_STATIC_DATA,
        ITEM_STATIC_DATA_LIST,
        SKIN_DATA_LIST,
        PASSIVE_SKILLS,
        PASSIVE_SKILLS_LIST,
        ACTIVE_SKILLS,
        ACTIVE_SKILLS_LIST,
        TECH_LV_DICT,
        PAL_TEMPLATES,
        SKILL_TEMPLATES,
        PAL_CONTAINERS,
        PAL_TRANSFER_CONFLICT,
        BASE_CAMP_RESEARCH,
        SELECTED_RESEARCH_GUILD_ID,

        getTranslatedText,
        getTechName,
        getMessageText,

        elementIconKey,
        palElementKeys,
        passiveTier,
        genderKey,
        specialTypeKeys,
        filterSkillOptions,
        isSkillAssignable,
        skillBadges,
        skillBadgeTranslationKey,

        reset,
        clearPalTransferConflict,

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
            addEquipWaza,
            addMasteredWaza,
            addPal,
            addPassiveSkill,
            applySkillTemplate,
            auth,
            bootstrap,
            changeSpecies,
            completeBaseCampResearch,
            connectBackend,
            delPal,
            deletePalTemplate,
            deleteSkillTemplate,
            dumpPalData,
            dupePal,
            fetchBaseCampResearch,
            fetchPalContainers,
            fetchPalTemplates,
            fetchSkillTemplates,
            fetch_config,
            friendshipDown,
            friendshipUp,
            get_updates,
            jumpToConflictingPal,
            loadPlayerInventory,
            loadSave,
            maxFriendship,
            maxSuitabilities,
            maximizePal,
            movePal,
            palLevelDown,
            palLevelUp,
            palMaxLevel,
            patchInventorySlot,
            path_back,
            playerLevelDown,
            playerLevelUp,
            playerMaxLevel,
            removeEquipWaza,
            removeMasteredWaza,
            removePassiveSkill,
            renameSkillTemplate,
            savePalTemplate,
            saveSkillTemplate,
            selectPal,
            selectPlayer,
            setStatusPoint,
            showDonate,
            show_file_picker,
            shownDonate,
            suitabilityDown,
            suitabilityUp,
            swapBoss,
            swapGender,
            swapRare,
            toggleAwakening,
            toggleTech,
            unlock,
            updateConflictingPal,
            updateI18n,
            updatePal,
            updatePlayer,
            update_picker_result,
            writeSave,
        }),
    };
});
