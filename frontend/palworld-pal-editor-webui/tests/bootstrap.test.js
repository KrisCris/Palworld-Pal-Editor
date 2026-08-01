import assert from "node:assert/strict";
import test from "node:test";

import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { backendStorageKey } from "../src/services/backend-connection.js";

const values = new Map();
globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
};
globalThis.window = { location: { origin: "http://frontend.test" } };
globalThis.alert = () => {};

const { usePalEditorStore } = await import("../src/stores/paleditor.js");

const reply = data => ({ data: { status: 0, data } });

function newStore({ preserveStorage = false } = {}) {
    if (!preserveStorage) values.clear();
    setActivePinia(createPinia());
    return usePalEditorStore();
}

function mockBackend({
    password = true,
    loaded = false,
    hasWorkingPal = false,
    players = [],
    pals = [],
    locale = "en",
    locales = { en: "English" },
} = {}) {
    const calls = [];
    axios.get = async url => {
        calls.push(["GET", url]);
        if (url.endsWith("fetch_config")) {
            return reply({
                I18n: locale,
                I18nList: locales,
                Path: "C:/save",
                HasPassword: password,
                VERSION: "test",
                IsOfficialBuild: false,
            });
        }
        if (url.endsWith("/auth")) return reply(null);
        if (url.endsWith("/status")) return reply({ SaveLoaded: loaded });
        if (url.endsWith("players_data")) {
            return reply({ hasWorkingPal, players });
        }
        if (url.endsWith("passive_skills") || url.endsWith("active_skills") || url.endsWith("pal_data")) {
            return reply({ dict: {}, arr: [] });
        }
        if (url.endsWith("tech_data")) return reply({ techLvDict: {} });
        if (url.endsWith("skin_data")) return reply({ arr: [] });
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.patch = async url => {
        calls.push(["PATCH", url]);
        return reply(null);
    };
    axios.post = async (url, data) => {
        calls.push(["POST", url]);
        if (url.endsWith("/login")) return reply({ access_token: "token" });
        if (url.endsWith("/save/load")) return reply(null);
        if (url.endsWith("/player_pals")) return reply(pals);
        if (url.endsWith("/paldata")) {
            return reply(pals.find(pal => pal.InstanceId === data.InstanceId));
        }
        if (url.endsWith("/player_data")) {
            return reply(players.find(player => player.InstanceId === data.PlayerUId));
        }
        throw new Error(`Unexpected POST ${url}`);
    };
    return calls;
}

test("connectBackend promotes a reachable candidate and routes its asset URLs", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true });

    assert.equal(await store.connectBackend("10.0.0.2:58081"), true);
    assert.equal(calls[0][1], "http://10.0.0.2:58081/api/save/fetch_config");
    assert.equal(store.BACKEND_ORIGIN, "http://10.0.0.2:58081");
    assert.equal(store.BACKEND_CONNECTED, true);
    assert.deepEqual(store.BACKEND_RECENT, ["http://10.0.0.2:58081"]);
    assert.equal(store.backendAssetUrl("/image/ui/heal"), "http://10.0.0.2:58081/image/ui/heal");
});

test("connectBackend keeps the persisted origin when the candidate cannot fetch config", async () => {
    const store = newStore();
    mockBackend({ password: true });
    await store.connectBackend("10.0.0.1:58081");
    const previousState = store.APP_STATE;
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    assert.equal(await store.connectBackend("10.0.0.2:58081"), false);
    assert.equal(store.BACKEND_ORIGIN, "http://10.0.0.1:58081");
    assert.equal(store.BACKEND_CANDIDATE, "http://10.0.0.1:58081");
    assert.equal(store.BACKEND_CONNECTED, true);
    assert.equal(store.APP_STATE, previousState);
    assert.equal(store.BACKEND_ERROR, null);
    assert.equal(localStorage.getItem("PAL_BACKEND_ORIGIN"), "http://10.0.0.1:58081");
});

test("a persisted backend is disconnected until its initial probe succeeds", async () => {
    values.clear();
    localStorage.setItem("PAL_BACKEND_ORIGIN", "http://10.0.0.1:58081");
    const store = newStore({ preserveStorage: true });
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    await store.bootstrap();

    assert.equal(store.BACKEND_CONNECTED, false);
});

test("a failed probe preserves the active backend's ephemeral token", async () => {
    const store = newStore();
    mockBackend({ password: true });
    await store.bootstrap();
    await store.unlock("secret", false);
    assert.equal(localStorage.getItem("PAL_AUTH_TOKEN"), null);

    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };
    assert.equal(await store.connectBackend("10.0.0.2:58081"), false);

    axios.get = async (url, config) => {
        if (url.endsWith("fetch_config")) return reply({
            I18n: "en", I18nList: { en: "English" }, Path: "C:/save", HasPassword: true,
        });
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, "Bearer token");
            return reply(null);
        }
        if (url.endsWith("/status")) return reply({ SaveLoaded: false });
        throw new Error(`Unexpected GET ${url}`);
    };

    assert.equal(await store.connectBackend(""), true);
    assert.equal(store.APP_STATE, "entry");
});

test("candidate auth failures preserve the active backend token", async () => {
    const originA = "http://10.0.0.1:58081";
    const originB = "http://10.0.0.2:58081";
    values.clear();
    localStorage.setItem("PAL_BACKEND_ORIGIN", originA);
    localStorage.setItem(backendStorageKey("PAL_AUTH_TOKEN", originA), "token-a");
    const store = newStore({ preserveStorage: true });
    axios.get = async (url, config) => {
        if (url === `${originB}/api/save/fetch_config`) {
            assert.equal(config.headers.Authorization, "Bearer ");
            return { data: { status: 2, msg: "auth required" } };
        }
        if (url === `${originA}/api/save/fetch_config`) return reply({
            I18n: "en", I18nList: { en: "English" }, Path: "C:/save-a", HasPassword: true,
        });
        if (url === `${originA}/api/auth/auth`) {
            assert.equal(config.headers.Authorization, "Bearer token-a");
            return reply(null);
        }
        if (url === `${originA}/api/save/status`) return reply({ SaveLoaded: false });
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async () => reply(null);

    assert.equal(await store.connectBackend(originB), false);
    assert.equal(localStorage.getItem(backendStorageKey("PAL_AUTH_TOKEN", originA)), "token-a");
    await store.bootstrap(originA);
});

test("normalizes persisted origins and bootstrap candidates", async () => {
    values.clear();
    localStorage.setItem("PAL_BACKEND_ORIGIN", "http://10.0.0.2:58081/");
    const store = newStore({ preserveStorage: true });
    const calls = mockBackend({ password: true });

    assert.equal(store.BACKEND_ORIGIN, "http://10.0.0.2:58081");
    assert.equal(localStorage.getItem("PAL_BACKEND_ORIGIN"), "http://10.0.0.2:58081");
    await store.bootstrap("http://frontend.test/");
    assert.equal(calls[0][1], "/api/save/fetch_config");
    assert.equal(store.BACKEND_ORIGIN, "");
    assert.equal(localStorage.getItem("PAL_BACKEND_ORIGIN"), "");
});

test("backend credentials and paths are scoped to the selected origin", async () => {
    const originA = "http://10.0.0.1:58081";
    const originB = "http://10.0.0.2:58081";
    values.clear();
    localStorage.setItem("PAL_BACKEND_ORIGIN", originA);
    localStorage.setItem(backendStorageKey("PAL_AUTH_TOKEN", originA), "token-a");
    localStorage.setItem(backendStorageKey("PAL_GAME_SAVE_PATH", originA), "C:/save-a");
    localStorage.setItem(backendStorageKey("PAL_AUTH_TOKEN", originB), "token-b");
    localStorage.setItem(backendStorageKey("PAL_GAME_SAVE_PATH", originB), "C:/save-b");

    let expectedToken = "token-a";
    axios.get = async (url, config) => {
        if (url.endsWith("fetch_config")) return reply({
            I18n: "en", I18nList: { en: "English" }, Path: "C:/configured", HasPassword: true,
        });
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, `Bearer ${expectedToken}`);
            return reply(null);
        }
        if (url.endsWith("/status")) return reply({ SaveLoaded: false });
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async () => reply(null);

    let store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(store.PAL_GAME_SAVE_PATH, "C:/save-a");

    expectedToken = "token-b";
    localStorage.setItem("PAL_BACKEND_ORIGIN", originB);
    store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(store.PAL_GAME_SAVE_PATH, "C:/save-b");
});

test("legacy credentials and paths stay in same-origin mode", async () => {
    values.clear();
    localStorage.setItem("PAL_AUTH_TOKEN", "legacy-token");
    localStorage.setItem("PAL_GAME_SAVE_PATH", "C:/legacy-save");
    axios.get = async (url, config) => {
        if (url.endsWith("fetch_config")) {
            if (url.startsWith("http://10.0.0.2:58081")) {
                assert.equal(config.headers.Authorization, "Bearer ");
            }
            return reply({
            I18n: "en", I18nList: { en: "English" }, Path: "C:/configured", HasPassword: true,
            });
        }
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, "Bearer legacy-token");
            return reply(null);
        }
        if (url.endsWith("/status")) return reply({ SaveLoaded: false });
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async () => reply(null);

    const store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(store.PAL_GAME_SAVE_PATH, "C:/legacy-save");

    localStorage.setItem("PAL_BACKEND_ORIGIN", "http://10.0.0.2:58081");
    const remoteStore = newStore({ preserveStorage: true });
    await remoteStore.bootstrap();
    assert.equal(remoteStore.PAL_GAME_SAVE_PATH, "C:/configured");
});

test("connectBackend is unavailable while editing", async () => {
    const store = newStore();
    const calls = mockBackend({ password: false, loaded: true });
    await store.bootstrap();

    assert.equal(store.APP_STATE, "editor");
    assert.equal(await store.connectBackend("10.0.0.2:58081"), false);
    assert.equal(calls.at(-1)[1], "/api/save/skin_data");
});

test("bootstrap asks for a password when no remembered token exists", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true });

    await store.bootstrap();

    assert.equal(store.APP_STATE, "auth-required");
    assert.deepEqual(calls, [["GET", "/api/save/fetch_config"]]);
});

test("bootstrap resumes an already loaded backend save with a remembered token", async () => {
    const store = newStore();
    localStorage.setItem("PAL_AUTH_TOKEN", "remembered");
    const calls = mockBackend({ password: true, loaded: true });

    await store.bootstrap();

    assert.equal(store.APP_STATE, "editor");
    assert.equal(store.SAVE_LOADED_FLAG, true);
    assert.equal(store.PAL_WRITE_BACK_PATH, "C:/save");
    assert.ok(calls.some(call => call[1] === "/api/auth/auth"));
    assert.ok(calls.some(call => call[1] === "/api/save/status"));
    assert.equal(calls.some(call => call[1] === "/api/save/load"), false);
});

test("bootstrap logs in without a password and routes an empty backend to entry", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: false });

    await store.bootstrap();

    assert.equal(store.APP_STATE, "entry");
    assert.equal(store.SAVE_LOADED_FLAG, false);
});

test("unlock stores only remembered tokens and resumes backend state", async () => {
    const store = newStore();
    mockBackend({ password: true, loaded: false });
    await store.bootstrap();

    await store.unlock("secret", true);

    assert.equal(localStorage.getItem("PAL_AUTH_TOKEN"), "token");
    assert.equal(store.APP_STATE, "entry");
});

test("startup network failures route to the dedicated backend error state", async () => {
    const store = newStore();
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    await store.bootstrap();

    assert.equal(store.APP_STATE, "backend-error");
    assert.equal(store.BACKEND_ERROR.message, "Network Error");
});

test("runtime failures preserve editor state", async () => {
    const store = newStore();
    const calls = mockBackend({ password: false, loaded: true });
    await store.bootstrap();
    assert.equal(store.APP_STATE, "editor");

    axios.get = async url => {
        calls.push(["GET", url]);
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };
    await store.get_updates();
    assert.equal(store.APP_STATE, "editor");
    assert.equal(store.SAVE_LOADED_FLAG, true);
});

test("a failed path-picker request does not clear the current save path", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: false });
    await store.bootstrap();
    assert.equal(store.PAL_GAME_SAVE_PATH, "C:/save");

    const fail = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };
    axios.get = fail;
    axios.post = fail;
    await store.show_file_picker();

    assert.equal(store.PAL_GAME_SAVE_PATH, "C:/save");
    assert.equal(store.APP_STATE, "entry");
});

test("a transient post-login failure can reuse the in-memory session token", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true, loaded: false });
    await store.bootstrap();

    const backendGet = axios.get;
    let failStatus = true;
    axios.get = async url => {
        if (url.endsWith("/status") && failStatus) {
            failStatus = false;
            const error = new Error("Network Error");
            error.request = {};
            throw error;
        }
        return backendGet(url);
    };

    await store.unlock("secret", false);
    assert.equal(store.APP_STATE, "backend-error");

    await store.bootstrap();
    assert.equal(store.APP_STATE, "entry");
    assert.equal(calls.filter(call => call[1] === "/api/auth/login").length, 1);
});

test("startup stays connecting until loaded-save hydration completes", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: true });
    const backendGet = axios.get;
    let releasePlayers;
    axios.get = url => url.endsWith("players_data")
        ? new Promise(resolve => { releasePlayers = () => resolve(reply({ hasWorkingPal: false, players: [] })); })
        : backendGet(url);

    const boot = store.bootstrap();
    while (!releasePlayers) await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(store.APP_STATE, "connecting");
    assert.equal(store.SAVE_LOADED_FLAG, false);

    releasePlayers();
    await boot;
    assert.equal(store.APP_STATE, "editor");
});

test("mid-hydration authentication failure unlocks the password form", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: true });
    const backendGet = axios.get;
    axios.get = async url => {
        if (url.endsWith("players_data")) {
            const error = new Error("Unauthorized");
            error.response = {
                status: 401,
                statusText: "Unauthorized",
                data: { status: 2, msg: "Token expired" },
            };
            throw error;
        }
        return backendGet(url);
    };

    await store.bootstrap();

    assert.equal(store.APP_STATE, "auth-required");
    assert.equal(store.LOADING_FLAG, false);
});

test("a failed login request uses the dedicated backend error state", async () => {
    const store = newStore();
    mockBackend({ password: true, loaded: false });
    await store.bootstrap();
    axios.post = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    await store.unlock("secret", false);

    assert.equal(store.APP_STATE, "backend-error");
    assert.equal(store.LOADING_FLAG, false);
});

test("loaded-save hydration selects base camp again after reloading", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        hasWorkingPal: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
    });

    await store.bootstrap();
    assert.equal(store.BASE_PAL_BTN_CLK_FLAG, true);
    assert.equal(store.SELECTED_PLAYER_ID, null);

    await store.loadSave();
    assert.equal(store.BASE_PAL_BTN_CLK_FLAG, true);
    assert.equal(store.SELECTED_PLAYER_ID, null);
});

test("loaded-save hydration selects the first player when there is no base camp", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
    });

    await store.bootstrap();
    assert.equal(store.BASE_PAL_BTN_CLK_FLAG, false);
    assert.equal(store.SELECTED_PLAYER_ID, "player-1");

    await store.loadSave();
    assert.equal(store.BASE_PAL_BTN_CLK_FLAG, false);
    assert.equal(store.SELECTED_PLAYER_ID, "player-1");
});

test("selected Pal data retains its game-derived family", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{
            InstanceId: "pal-1",
            CharacterID: "Boss_Anubis",
            DataAccessKey: "Boss_Anubis",
            FamilyID: "Anubis",
        }],
    });

    await store.bootstrap();
    await store.selectPal("pal-1");

    assert.equal(store.SELECTED_PAL_DATA.FamilyID, "Anubis");
});

test("fetch_config publishes backend locales and accepts its untranslated locale", async () => {
    const store = newStore();
    const locales = {
        en: "English",
        de: "Deutsch",
        "zh-TW": "繁體中文",
    };
    mockBackend({ password: false, locale: "de", locales });

    await store.bootstrap();

    assert.deepEqual(store.I18nList, locales);
    assert.equal(store.I18n, "de");
    assert.equal(store.getTranslatedText("BackendError_Title"), "Something went wrong");
});

test("healing all pals does not try to reselect a missing pal", async t => {
    const store = newStore();
    const calls = mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
    });
    const alerts = [];
    globalThis.alert = message => alerts.push(message);
    t.after(() => { globalThis.alert = () => {}; });

    await store.bootstrap();
    assert.equal(store.SELECTED_PAL_ID, null);
    await store.updatePal({ target: { name: "heal_all_pals", value: "" } });

    assert.ok(calls.some(call => call[0] === "PATCH" && call[1] === "/api/pal/paldata"));
    assert.deepEqual(alerts, []);
});

test("wrong passwords remain on the auth page with inline feedback", async () => {
    const store = newStore();
    mockBackend({ password: true });
    await store.bootstrap();
    axios.post = async () => ({
        data: { status: 2, msg: "wrong password" },
    });

    await store.unlock("wrong", false);

    assert.equal(store.APP_STATE, "auth-required");
    assert.equal(store.AUTH_MESSAGE_KEY, "AuthView_Wrong_Password");
});

test("expired sessions retain an inline authentication explanation", () => {
    const store = newStore();

    store.requireAuth("AuthView_Session_Expired");

    assert.equal(store.APP_STATE, "auth-required");
    assert.equal(store.AUTH_MESSAGE_KEY, "AuthView_Session_Expired");
});

test("missing player validation uses a nonblocking warning", async () => {
    const store = newStore();

    await store.updatePlayer({ target: { name: "Rank", value: 1 } });

    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Select_Player");
    assert.equal(store.CURRENT_MESSAGE.severity, "warning");
    assert.equal(store.CURRENT_MESSAGE.presentation, "toast");
    assert.equal(store.LOADING_FLAG, false);
});

test("unexpected request errors release loading before showing details", async t => {
    const store = newStore();
    const originalConsoleError = console.error;
    console.error = () => {};
    t.after(() => { console.error = originalConsoleError; });
    axios.post = async () => { throw new TypeError("broken request adapter"); };

    await store.writeSave();

    assert.equal(store.LOADING_FLAG, false);
    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Unexpected_Frontend_Error");
    assert.match(store.CURRENT_MESSAGE.log, /broken request adapter/);
});

test("donation failures do not open the donation panel", async () => {
    const store = newStore();
    axios.get = async () => ({
        data: { status: 1, msg: "donation unavailable" },
    });

    assert.equal(await store.showDonate(), false);
    assert.equal(store.CURRENT_MESSAGE.args[0].translationKey, "Operation_Donation");
});

test("successful saves use a nonblocking success message", async () => {
    const store = newStore();
    axios.post = async url => {
        assert.equal(url, "/api/save/save");
        return reply(null);
    };
    store.PAL_WRITE_BACK_PATH = "C:/output";

    await store.writeSave();

    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Save_Success");
    assert.deepEqual(store.CURRENT_MESSAGE.args, ["C:/output"]);
    assert.equal(store.CURRENT_MESSAGE.severity, "success");
    assert.equal(store.CURRENT_MESSAGE.presentation, "toast");
});
