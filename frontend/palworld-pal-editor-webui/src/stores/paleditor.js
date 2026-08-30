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
    UI_TRANSLATIONS,
} from "../i18n/index.js";
import { setBackendContext } from "../api/http.js";
import { useAppStore } from "./app.js";
import { useCatalogsStore } from "./catalogs.js";
import { usePalsStore } from "./pals.js";
import { useResearchStore } from "./research.js";
import { usePlayersStore } from "./players.js";
import { BASE_ROSTER_KEY, useRostersStore } from "./rosters.js";
import { useSessionStore } from "./session.js";
import { useStoragesStore } from "./storages.js";
import { useTemplatesStore } from "./templates.js";

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
    // connection, the static catalogs, templates and the choreography around the
    // writes -- which list to open, which Pal to select, what to say when one
    // fails. The save itself lives in `stores/session`, and its Pals, players,
    // rosters and storages in the stores below -- this store reads them, and
    // nothing reads back into it.
    const session = useSessionStore();
    const app = useAppStore();
    const catalogs = useCatalogsStore();
    const pals = usePalsStore();
    const research = useResearchStore();
    const players = usePlayersStore();
    const rosters = useRostersStore();
    const storages = useStoragesStore();
    const templates = useTemplatesStore();

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
    const MAX_EQUIP_WAZA = 3;

    // flags
    const SHOW_DONATE_FLAG = ref(false);
    const UPDATE_PAL_RESELECT_CTR = ref(0);
    const HIDE_INVALID_OPTIONS = ref(true);
    const PAL_SAVE_DETAILS_OPEN = ref(false);

    // A base camp is worth listing even when nobody works in it yet, so the base
    // roster button follows the storages as well as the roster listing.
    const HAS_WORKING_PAL_FLAG = computed(
        () => rosters.hasBaseRoster || storages.hasBaseStorage,
    );

    const PAL_PASSIVE_SELECTED_ITEM = ref("");
    const PAL_ACTIVE_SELECTED_ITEM = ref("");

    // Configs
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
    const backendAssetUrl = path => versionedBackendAssetUrl(BACKEND_ORIGIN.value, path, app.version);
    const storageKey = name => backendStorageKey(name, BACKEND_ORIGIN.value);
    // Reading the remembered path is what puts it back on `session`; the picker
    // opens on it, which is why the answer is kept.
    app.pickerPath = session.recallSavePath(localStorage, BACKEND_ORIGIN.value);

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
    // Synchronous because `bootstrap` sends its first request in the same tick
    // as it points the app at a new backend; a deferred watcher would publish the
    // origin after that request had already gone to the old one.
    watch(
        BACKEND_REQUEST_ORIGIN,
        origin => setBackendContext({ origin }),
        { flush: "sync" },
    );
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
            setConnectionError(error);
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
        else if (error.isConnectionFailure) setConnectionError(error);
        else setBackendError(getTranslatedText("BackendError_Request_Failed", [error.message]));
    }

    // A backend that never answered is the failure the error screen has its own
    // shape for: the fix is choosing a different backend, not retrying this one.
    function setConnectionError(error) {
        BACKEND_CONNECTED.value = false;
        setBackendError({ kind: "connection", message: error.message });
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
            templates.clear();
            setAuthToken(readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");
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
        else setAuthToken(auth_token || readStorage(localStorage, storageKey("PAL_AUTH_TOKEN")) || "");

        if (!await loadAppConfig(BACKEND_CANDIDATE.value)) {
            BACKEND_REQUEST_ORIGIN.value = BACKEND_ORIGIN.value;
            return false;
        }
        if (app.hasPassword) {
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
            auth_token = previousToken;
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
                    refreshSucceeded = await fetchBaseCampResearch();
                }
            }
        }
        return refreshSucceeded;
    }

    // Six sequential requests before this task, each with its own copy of the
    // same three-branch status ladder. The catalogs are what they answer with;
    // reporting the failure is what stays here.
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

        PAL_PASSIVE_SELECTED_ITEM.value = "";
        PAL_ACTIVE_SELECTED_ITEM.value = "";
        templates.clear();
        storages.clear();
        research.clear();

        if (updateAppState) {
            session.appState = IS_LOCKED.value ? "auth-required" : "entry";
        }
    }

    function getTranslatedText(translationKey, args = []) {
        let translation = UI_TRANSLATIONS[app.locale]?.[translationKey]
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

    // ---- players -------------------------------------------------------------
    // The store owns the player and its inventory; what stays here is the DOM
    // events the existing controls fire and the reporting they need.

    // Called straight from `@click` on the field buttons, whose `name` is the
    // field to write and whose `value` is what to write into it. The backend's
    // allowlist decides whether that name is writable -- it is not a method name
    // any more.
    function updatePlayer(e) {
        return applyPlayerPatch({ [e.target.name]: e.target.value });
    }

    async function applyPlayerPatch(patch) {
        try {
            if (await players.update(patch) === null) showToast("Message_Select_Player");
        } catch (error) {
            reportApiFailure(error, "Operation_Update_Player");
        }
    }

    function playerLevelDown() {
        const player = players.selectedPlayer;
        if (!player || player.Level <= 1) return;
        return applyPlayerPatch({ Level: player.Level - 1 });
    }

    function playerLevelUp() {
        const player = players.selectedPlayer;
        const ceiling = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        if (!player || player.Level >= ceiling) return;
        return applyPlayerPatch({ Level: player.Level + 1 });
    }

    function playerMaxLevel() {
        return applyPlayerPatch({
            Level: HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL,
        });
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
        // A stat point can also be bought with an item, so it is spent against
        // the total; every other kind is the plain allocation.
        const field = player.StatusPointMetadata[name]?.category === "stat"
            ? "StatusPointTotals"
            : "StatusPoints";
        return applyPlayerPatch({ [field]: { [name]: points } });
    }

    // The technology field takes the list the player should end up with, so both
    // of these send one: §8.3's rule for skills, applied to the same shape.
    // Locking compares case-insensitively for the same reason the cards do --
    // the save's spelling of a technology need not be the catalog's, and an
    // exact filter would quietly leave it unlocked.
    function toggleTech(tech, status) {
        const unlocked = players.selectedPlayer?.UnlockedRecipeTechnologyNames ?? [];
        return applyPlayerPatch({
            UnlockedRecipeTechnologyNames: status
                ? [...unlocked, tech]
                : unlocked.filter(
                    name => name.toLowerCase() !== tech.toLowerCase(),
                ),
        });
    }

    // The union, not the catalog: this field is a replacement, so sending the
    // catalog alone would lock anything the save has that the catalog does not
    // -- including everything, if the catalog were somehow empty. Unlocking all
    // of them has never been able to take one away, and still cannot.
    function unlockAllTechs() {
        const unlocked = players.selectedPlayer?.UnlockedRecipeTechnologyNames ?? [];
        const everything = Object.values(catalogs.technologiesByLevel)
            .flat()
            .map(tech => tech.InternalName);
        return applyPlayerPatch({
            UnlockedRecipeTechnologyNames: [...unlocked, ...everything],
        });
    }

    async function loadPlayerInventory() {
        try {
            return await players.loadInventory() !== null;
        } catch (error) {
            reportApiFailure(error, "Operation_Load_Player_Data");
            return false;
        }
    }

    // The reply is the whole inventory, so the reload this used to do afterwards
    // is that same request, answered once.
    async function patchInventorySlot(containerKind, slotIndex, itemId, count) {
        try {
            return await players.updateInventorySlot(
                containerKind,
                slotIndex,
                itemId,
                count,
                !HIDE_INVALID_OPTIONS.value,
            ) !== null;
        } catch (error) {
            reportApiFailure(error, "Operation_Update_Player");
            return false;
        }
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
        try {
            return await research.load();
        } catch (error) {
            reportApiFailure(error, "Operation_BaseCamp_Research");
            return false;
        }
    }

    async function completeBaseCampResearch(scope) {
        try {
            const changed = await research.complete(scope);
            if (changed === null) return false;
            showToast("Message_BaseCamp_Research_Completed", "success", [changed]);
            return true;
        } catch (error) {
            reportApiFailure(error, "Operation_BaseCamp_Research");
            return false;
        }
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
    // The store owns the Pal and the writes; what stays here is the DOM events
    // the existing controls fire, the catalog questions the UI asks before
    // sending, and the reporting.

    // Called straight from `@click`/`@change`, whose `name` is the field to write
    // and whose `value` is what to write into it. Whether that name may be
    // written is the backend allowlist's answer, not a method lookup. The
    // operation gate is `gated()`, applied to the whole exported surface.
    function updatePal(e) {
        return applyPalPatch({ [e.target.name]: e.target.value });
    }

    function applyPalPatch(patch) {
        return runPalWrite(() => pals.update(patch), "Operation_Update_Pal");
    }

    // Every Pal write answers with the Pal it changed, so none of them re-reads
    // it afterwards. `null` means no Pal is open, which these controls cannot
    // reach: they are rendered only while one is.
    async function runPalWrite(write, operation) {
        try {
            if (await write() === null) return false;
            UPDATE_PAL_RESELECT_CTR.value++;
            return true;
        } catch (error) {
            reportApiFailure(error, operation);
            return false;
        }
    }

    // A skill group is submitted whole. These build the list the Pal should end
    // up with; the backend refuses one the game cannot resolve.
    function replaceSkills(group, skills) {
        return runPalWrite(
            () => pals.replaceSkills(group, skills),
            "Operation_Update_Pal",
        );
    }

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
        return applyPalPatch({ IsRarePal: !editedPal().IsRarePal });
    }

    function swapBoss() {
        return applyPalPatch({ IsBOSS: !editedPal().IsBOSS });
    }

    function toggleAwakening() {
        return applyPalPatch({ IsAwakening: !editedPal().IsAwakening });
    }

    function palLevelDown() {
        const pal = editedPal();
        if (pal.Level <= 1) return;
        return applyPalPatch({ Level: pal.Level - 1 });
    }

    function palLevelUp() {
        const pal = editedPal();
        const ceiling = HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL;
        if (pal.Level >= ceiling) return;
        return applyPalPatch({ Level: pal.Level + 1 });
    }

    function palMaxLevel() {
        return applyPalPatch({
            Level: HIDE_INVALID_OPTIONS.value ? MAX_LEVEL : MAX_INVALID_LEVEL,
        });
    }

    function friendshipDown() {
        const pal = editedPal();
        if (pal.FriendshipLevel <= -3) return;
        return applyPalPatch({ FriendshipLevel: pal.FriendshipLevel - 1 });
    }

    function friendshipUp() {
        const pal = editedPal();
        if (pal.FriendshipLevel >= MAX_FRIENDSHIP_LEVEL) return;
        return applyPalPatch({ FriendshipLevel: pal.FriendshipLevel + 1 });
    }

    function maxFriendship() {
        return applyPalPatch({ FriendshipLevel: MAX_FRIENDSHIP_LEVEL });
    }

    function swapGender() {
        const gender = editedPal().Gender;
        let next = HIDE_INVALID_OPTIONS.value ? "NONE" : "EPalGenderType::Female";
        if (gender == "EPalGenderType::Female") next = "EPalGenderType::Male";
        if (gender == "EPalGenderType::Male") next = "EPalGenderType::Female";
        return applyPalPatch({ Gender: next });
    }

    // A skill the game has no entry for is one the backend would refuse, and one
    // the UI cannot draw either -- so the dropdown selections are checked here
    // before a request is worth making. The `Invalid`/human rules are the same
    // check the skill picker already greys the option out with.
    function assignableActiveSkill(skill) {
        const active = catalogs.activeSkillsByName[skill];
        if (!active) return false;
        return !HIDE_INVALID_OPTIONS.value
            || isSkillAssignable(active, pals.selectedPal?.IsHuman);
    }

    function removePassiveSkill(e) {
        return replaceSkills(
            "passive",
            editedPal().PassiveSkillList.filter(skill => skill !== e.target.name),
        );
    }

    function addPassiveSkill() {
        const skill = PAL_PASSIVE_SELECTED_ITEM.value;
        if (!catalogs.passiveSkillsByName[skill]) {
            showToast("Message_Select_Skill");
            return;
        }
        if (HIDE_INVALID_OPTIONS.value && editedPal().PassiveSkillList.length >= 4) {
            showToast("Message_Passive_Limit");
            return;
        }
        return replaceSkills("passive", [...editedPal().PassiveSkillList, skill]);
    }

    function removeEquipWaza(e) {
        return replaceSkills(
            "equipped",
            editedPal().EquipWaza.filter(waza => waza !== e.target.name),
        );
    }

    function addEquipWaza(e) {
        if (!assignableActiveSkill(e.target.name)) {
            showToast("Message_Skill_Not_Assignable");
            return;
        }
        // Equipping a move also learns it, so this one list says both.
        return replaceSkills("equipped", [...editedPal().EquipWaza, e.target.name]);
    }

    function removeMasteredWaza(e) {
        return replaceSkills(
            "mastered",
            editedPal().MasteredWaza.filter(waza => waza !== e.target.name),
        );
    }

    function addMasteredWaza() {
        const skill = PAL_ACTIVE_SELECTED_ITEM.value;
        if (!catalogs.activeSkillsByName[skill]) {
            showToast("Message_Select_Skill");
            return;
        }
        if (!assignableActiveSkill(skill)) {
            showToast("Message_Skill_Not_Assignable");
            return;
        }
        const pal = editedPal();
        // Learning a move with an active slot free has always equipped it too,
        // and equipping is what learns it -- so the equipped list carries both.
        if (pal.EquipWaza.length < MAX_EQUIP_WAZA) {
            return replaceSkills("equipped", [...pal.EquipWaza, skill]);
        }
        return replaceSkills("mastered", [...pal.MasteredWaza, skill]);
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
        return applyPalPatch({ Suitabilities: { [name]: value } });
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
        return applyPalPatch({ Suitabilities: values });
    }

    function changeSpecies(characterId) {
        return applyPalPatch({ CharacterID: characterId });
    }

    // The three buttons the editor and the top bar show are one operation: curing
    // an illness and reviving a fainted Pal already ran the same code.
    function healPal() {
        return runPalWrite(() => pals.heal(), "Operation_Update_Pal");
    }

    async function healAllPals() {
        try {
            await pals.healAll();
        } catch (error) {
            reportApiFailure(error, "Operation_Update_Pal");
            return false;
        }
        // The reply names every roster but no record, so nothing in it can say
        // what the heal did to the Pal on screen; that one is re-read.
        if (pals.selectedRecordKey) await refreshPal(pals.selectedRecordKey);
        return true;
    }

    // The export button copies the Pal as its own storage writes it, formatted
    // here rather than by the backend: what crosses the wire is the record, and
    // indentation is a property of what lands on the clipboard.
    async function dumpPalData() {
        let record;
        try {
            record = await pals.nativeRecord();
        } catch (error) {
            reportApiFailure(error, "Operation_Copy_Pal");
            return false;
        }
        try {
            await navigator.clipboard.writeText(JSON.stringify(record, null, 4));
        } catch (error) {
            // Refusing the clipboard is the browser's to do, and it is the only
            // half of this that was never a request.
            reportFrontendError(error, getTranslatedText("Operation_Copy_Pal"));
            return false;
        }
        showToast("Message_Pal_Copied", "success");
        return true;
    }

    async function maximizePal() {
        if (!await runPalWrite(() => pals.maximize(), "Operation_Maximize_Pal")) {
            return false;
        }
        showToast("Message_Pal_Maximized", "success");
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
        if (successor && pals.summary(successor)) await selectPal(successor);
        return true;
    }

    // Which targets the move dialog may offer for the Pal on screen. One request
    // per target, for the group being looked at: whether a Pal may go somewhere
    // is the backend's answer about that pair, not something a storage or a
    // storage kind can be asked on its own (spec §8.2).
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
        return selectPal(result.resultRecord.recordKey);
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
        return selectPal(target.recordKey);
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
        await selectPal(result.resultRecord.recordKey);
        return true;
    }

    async function dupePal() {
        let result;
        try {
            result = await pals.duplicate(pals.selectedRecordKey);
        } catch (error) {
            reportApiFailure(error, "Operation_Duplicate_Pal");
            return false;
        }
        await selectPal(result.resultRecord.recordKey);
        return true;
    }

    // ---- templates -----------------------------------------------------------
    // The templates themselves live in `stores/templates`; what stays here is the
    // gate, the reporting and the toast, which is the same three lines for all
    // seven of them.

    async function runTemplateAction(action, operationKey, toastKey) {
        try {
            await action();
        } catch (error) {
            reportApiFailure(error, operationKey);
            return false;
        }
        if (toastKey) showToast(toastKey, "success");
        return true;
    }

    function fetchPalTemplates() {
        return runTemplateAction(
            () => templates.loadPalTemplates(),
            "Operation_Load_Pal_Templates",
        );
    }

    function savePalTemplate(name) {
        if (!pals.selectedRecordKey) return false;
        return runTemplateAction(
            () => templates.savePalTemplate(name, pals.selectedRecordKey),
            "Operation_Save_Pal_Template",
            "Message_Pal_Template_Saved",
        );
    }

    function deletePalTemplate(templateId) {
        return runTemplateAction(
            () => templates.removePalTemplate(templateId),
            "Operation_Delete_Pal_Template",
            "Message_Pal_Template_Deleted",
        );
    }

    function fetchSkillTemplates() {
        return runTemplateAction(
            () => templates.loadSkillTemplates(),
            "Operation_Load_Skill_Templates",
        );
    }

    function saveSkillTemplate(type, name) {
        if (!pals.selectedRecordKey) return false;
        return runTemplateAction(
            () => templates.saveSkillTemplate(name, type, pals.selectedRecordKey),
            "Operation_Save_Skill_Template",
            "Message_Skill_Template_Saved",
        );
    }

    function renameSkillTemplate(templateId, name) {
        return runTemplateAction(
            () => templates.renameTemplate(templateId, name),
            "Operation_Rename_Skill_Template",
            "Message_Skill_Template_Renamed",
        );
    }

    // Applying one is a Pal write, not a template read: it answers with the Pal
    // it changed, so nothing is re-read afterwards.
    async function applySkillTemplate(templateId) {
        if (!await runPalWrite(
            () => pals.applyTemplate(templateId), "Operation_Apply_Skill_Template",
        )) return false;
        showToast("Message_Skill_Template_Applied", "success");
        return true;
    }

    function deleteSkillTemplate(templateId) {
        return runTemplateAction(
            () => templates.removeSkillTemplate(templateId),
            "Operation_Delete_Skill_Template",
            "Message_Skill_Template_Deleted",
        );
    }

    function palElementKeys(DataAccessKey) {
        return (catalogs.palsByName[DataAccessKey]?.Elements ?? [])
            .map(elementIconKey)
            .filter(Boolean);
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
            browseParentPath,
            browseSavePath,
            changeSpecies,
            completeBaseCampResearch,
            connectBackend,
            delPal,
            deletePalTemplate,
            deleteSkillTemplate,
            dumpPalData,
            dupePal,
            fetchBaseCampResearch,
            fetchPalTemplates,
            fetchSkillTemplates,
            friendshipDown,
            friendshipUp,
            healAllPals,
            healPal,
            jumpToConflictingPal,
            loadCreationTargets,
            loadLatestRelease,
            loadMoveTargets,
            loadPlayerInventory,
            loadSave,
            maxFriendship,
            maxSuitabilities,
            maximizePal,
            movePal,
            openFilePicker,
            palLevelDown,
            palLevelUp,
            palMaxLevel,
            patchInventorySlot,
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
            shownDonate,
            suitabilityDown,
            suitabilityUp,
            swapBoss,
            swapGender,
            swapRare,
            toggleAwakening,
            toggleTech,
            unlock,
            unlockAllTechs,
            updateConflictingPal,
            updateI18n,
            updatePal,
            updatePlayer,
            writeSave,
        }),
    };
});
