import assert from "node:assert/strict";
import test from "node:test";

import axios from "axios";
import { createPinia, setActivePinia } from "pinia";

const values = new Map();
globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
};
globalThis.alert = () => {};

const { usePalEditorStore } = await import("../src/stores/paleditor.js");

const reply = data => ({ data: { status: 0, data } });

function newStore() {
    values.clear();
    setActivePinia(createPinia());
    return usePalEditorStore();
}

function mockBackend({
    password = true,
    loaded = false,
    hasWorkingPal = false,
    players = [],
} = {}) {
    const calls = [];
    axios.get = async url => {
        calls.push(["GET", url]);
        if (url.endsWith("fetch_config")) {
            return reply({
                I18n: "en",
                I18nList: { en: "English" },
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
        if (url.endsWith("/player_pals")) return reply([]);
        if (url.endsWith("/player_data")) {
            return reply(players.find(player => player.InstanceId === data.PlayerUId));
        }
        throw new Error(`Unexpected POST ${url}`);
    };
    return calls;
}

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
