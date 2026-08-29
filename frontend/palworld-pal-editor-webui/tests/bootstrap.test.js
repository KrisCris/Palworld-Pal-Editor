import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
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
const { useAppStore } = await import("../src/stores/app.js");
const { useCatalogsStore } = await import("../src/stores/catalogs.js");
const { useSessionStore } = await import("../src/stores/session.js");
const { usePalsStore } = await import("../src/stores/pals.js");
const { usePlayersStore } = await import("../src/stores/players.js");
const { useResearchStore } = await import("../src/stores/research.js");
const { useRostersStore } = await import("../src/stores/rosters.js");
let appState;
let session;
let pals;
let players;
let research;
let rosters;

const reply = data => ({ data: { status: 0, data } });
// What `GET /api/app-config` answers, for the tests that mock axios themselves
// rather than going through `mockBackend`.
const appConfigFor = defaultSavePath => ({
    i18n: "en",
    i18nOptions: { en: "English" },
    defaultSavePath,
    hasPassword: true,
    version: "test",
    isOfficialBuild: false,
    donationPromptDismissed: false,
});
// REST resources answer with the resource itself, not the old envelope.
const resource = body => ({ data: body });
// The five §8.4 catalogs, each empty. No test here asserts on their contents --
// what they assert is that the editor does not open until all five have answered.
const emptyCatalog = url => ({
    "/api/catalogs/pals": { pals: [] },
    "/api/catalogs/skills": { passive: [], active: [] },
    "/api/catalogs/items": { items: [] },
    "/api/catalogs/technologies": { byLevel: {} },
    "/api/catalogs/skins": { skins: [] },
}[url.slice(url.indexOf("/api/catalogs/"))]);

function newStore({ preserveStorage = false } = {}) {
    if (!preserveStorage) values.clear();
    setActivePinia(createPinia());
    appState = useAppStore();
    session = useSessionStore();
    pals = usePalsStore();
    players = usePlayersStore();
    research = useResearchStore();
    rosters = useRostersStore();
    return usePalEditorStore();
}

// A `PalSummary` with only the fields a test cares about spelled out. The rest
// are the shape the backend always sends, so a store that reads one of them by a
// name the API does not use fails here rather than in the browser.
const summary = (overrides = {}) => ({
    recordKey: `world:${overrides.InstanceId ?? "pal"}`,
    InstanceId: overrides.InstanceId ?? "pal",
    CharacterID: "SheepBall",
    DisplayName: "Sheepball",
    DataAccessKey: "SheepBall",
    Paldeck: "001",
    storageKey: "world-container:palbox",
    storageKind: "world",
    storageOwnerPlayerUid: null,
    containerKind: "storage",
    containerLabel: null,
    ContainerId: "palbox",
    SlotIndex: 0,
    FavoriteIndex: 0,
    isAway: false,
    changeState: "unchanged",
    ...overrides,
});

const detail = (overrides = {}) => ({
    ...summary(overrides),
    groupId: null,
    EquipWaza: [],
    MasteredWaza: [],
    PassiveSkillList: [],
    Suitabilities: {},
    SuitabilityMinimums: {},
    ...overrides,
});

// The one shape every Pal write answers with (spec §8.3). A write that changed a
// Pal carries it back as a full detail, which is why nothing re-reads it.
const operation = (record, extra = {}) => ({
    resultRecord: record ? detail({ changeState: "modified", ...record }) : null,
    deletedRecordKeys: [],
    affectedRosterKeys: [],
    affectedStorageKeys: [],
    ...extra,
});

const SKILL_FIELDS = {
    passive: "PassiveSkillList",
    equipped: "EquipWaza",
    mastered: "MasteredWaza",
};

function mockBackend({
    password = true,
    loaded = false,
    hasWorkingPal = false,
    globalPalbox = false,
    players: playerRows = [],
    pals: palRows = [],
    containers = [],
    locale = "en",
    locales = { en: "English" },
} = {}) {
    const calls = [];
    const rosterEntries = [
        ...playerRows.map(player => ({
            rosterKey: `player:${player.InstanceId}`,
            kind: "player",
            label: player.NickName ?? "",
            playerUid: player.InstanceId,
        })),
        ...(hasWorkingPal
            ? [{ rosterKey: "base-workers", kind: "base", label: null, playerUid: null }]
            : []),
        ...(globalPalbox
            ? [{
                rosterKey: "global-palbox",
                kind: "global_palbox",
                label: "Global Palbox",
                playerUid: null,
            }]
            : []),
    ];
    const rows = palRows.map(pal => summary(pal));

    const appConfig = {
        i18n: locale,
        i18nOptions: locales,
        defaultSavePath: "C:/save",
        hasPassword: password,
        version: "test",
        isOfficialBuild: false,
        donationPromptDismissed: false,
    };

    axios.get = async url => {
        calls.push(["GET", url]);
        if (url.endsWith("/api/app-config")) return resource(appConfig);
        if (url.endsWith("/api/releases/latest")) {
            return resource({
                updateAvailable: false,
                version: null,
                downloadUrl: null,
                nexusUrl: "https://nexus.test",
            });
        }
        if (url.endsWith("/auth")) return reply(null);
        if (url.endsWith("/api/session")) {
            return resource({ loaded, path: loaded ? "C:/save" : null, warnings: [] });
        }
        if (url.endsWith("/api/rosters")) return resource(rosterEntries);
        if (url.endsWith("/api/players")) return resource(playerRows);
        if (url.endsWith("/api/pal/containers")) return reply(containers);
        const rosterPals = url.match(/\/api\/rosters\/([^/]+)\/pals$/);
        if (rosterPals) return resource(rows);
        const player = url.match(/\/api\/players\/(.+)$/);
        if (player) {
            const uid = decodeURIComponent(player[1]);
            return resource(playerRows.find(row => row.InstanceId === uid));
        }
        const pal = url.match(/\/api\/pals\/(.+)$/);
        if (pal) {
            const recordKey = decodeURIComponent(pal[1]);
            return resource(detail(
                rows.find(row => row.recordKey === recordKey) ?? { recordKey },
            ));
        }
        if (url.includes("/api/catalogs/")) return resource(emptyCatalog(url));
        // Selecting the base roster opens the research page with it.
        if (url.endsWith("/api/guild-research")) {
            return resource({ CategoryOrder: [], Guilds: [] });
        }
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.patch = async (url, body) => {
        calls.push(["PATCH", url]);
        if (url.endsWith("/api/app-config")) return resource(appConfig);
        const pal = url.match(/\/api\/pals\/([^/]+)$/);
        if (pal) {
            return resource(operation({ recordKey: decodeURIComponent(pal[1]), ...body }));
        }
        return reply(null);
    };
    axios.put = async (url, body) => {
        calls.push(["PUT", url]);
        if (url.endsWith("/api/session")) {
            return resource({ loaded: true, path: body?.path ?? "C:/save", warnings: [] });
        }
        const skills = url.match(/\/api\/pals\/([^/]+)\/skills\/(\w+)$/);
        if (skills) {
            return resource(operation({
                recordKey: decodeURIComponent(skills[1]),
                [SKILL_FIELDS[skills[2]]]: body.skills,
            }));
        }
        throw new Error(`Unexpected PUT ${url}`);
    };
    axios.post = async (url, body) => {
        calls.push(["POST", url]);
        if (url.endsWith("/login")) return reply({ access_token: "token" });
        if (url.endsWith("/api/pal-heals")) {
            return resource(body.scope === "all"
                ? operation(null, {
                    affectedRosterKeys: rosterEntries.map(entry => entry.rosterKey),
                })
                : operation({ recordKey: body.recordKey }));
        }
        const maximize = url.match(/\/api\/pals\/([^/]+)\/maximization$/);
        if (maximize) {
            return resource(operation({ recordKey: decodeURIComponent(maximize[1]) }));
        }
        throw new Error(`Unexpected POST ${url}`);
    };
    return calls;
}

test("connectBackend promotes a reachable candidate and routes its asset URLs", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true });

    assert.equal(await store.connectBackend("10.0.0.2:58081"), true);
    assert.equal(calls[0][1], "http://10.0.0.2:58081/api/app-config");
    assert.equal(store.BACKEND_ORIGIN, "http://10.0.0.2:58081");
    assert.equal(store.BACKEND_CONNECTED, true);
    assert.deepEqual(store.BACKEND_RECENT, ["http://10.0.0.2:58081"]);
    assert.equal(store.backendAssetUrl("/image/ui/heal"), "http://10.0.0.2:58081/image/ui/heal");
});

test("connectBackend keeps the persisted origin when the candidate cannot fetch config", async () => {
    const store = newStore();
    mockBackend({ password: true });
    await store.connectBackend("10.0.0.1:58081");
    const previousState = session.appState;
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    assert.equal(await store.connectBackend("10.0.0.2:58081"), false);
    assert.equal(store.BACKEND_ORIGIN, "http://10.0.0.1:58081");
    assert.equal(store.BACKEND_CANDIDATE, "http://10.0.0.1:58081");
    assert.equal(store.BACKEND_CONNECTED, true);
    assert.equal(session.appState, previousState);
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

test("one Pal is one entry: a roster refresh moves it without leaving a copy behind", async () => {
    // The bug the single cache exists to stop. The old store kept the Pal in the
    // roster it was viewed from and in the roster it moved to, and whichever copy
    // the editor happened to hold went on reporting the old container.
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{ InstanceId: "pal-1" }],
    });
    await store.bootstrap();
    await store.selectPal("world:pal-1");
    assert.equal(pals.selectedPal.containerKind, "storage");
    assert.equal(pals.palsByRecordKey.size, 1);

    axios.get = async url => (url.match(/\/api\/rosters\/([^/]+)\/pals$/)
        ? resource([summary({
            InstanceId: "pal-1",
            storageKey: "world-container:party",
            containerKind: "party",
        })])
        : resource(null));
    await rosters.loadRosterPals("player:player-1");

    assert.equal(pals.palsByRecordKey.size, 1);
    // The row moved, and so did the page reading it: there is nowhere for a stale
    // copy to survive.
    assert.equal(pals.summary("world:pal-1").containerKind, "party");
    assert.equal(pals.selectedPal.containerKind, "party");
});

test("a roster refresh keeps the detail the editor is showing", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{ InstanceId: "pal-1" }],
    });
    await store.bootstrap();
    await store.selectPal("world:pal-1");
    pals.selectedPal.PassiveSkillList.push("Legend");

    await rosters.loadRosterPals("player:player-1");

    assert.equal(pals.selectedPalLoaded, true);
    assert.deepEqual(pals.selectedPal.PassiveSkillList, ["Legend"]);
});

test("GPS conflicts lock updates to the matching Pal's actual container", async () => {
    const store = newStore();
    pals.applyDetail(detail({
        InstanceId: "gps-pal",
        recordKey: "gps:0",
        storageKind: "global_palbox",
    }));
    pals.selectedRecordKey = "gps:0";
    store.PAL_CONTAINERS = [{
        StorageKey: "world-container:palbox",
        StorageKind: "world",
        ContainerKind: "storage",
    }];
    axios.post = async (url, payload) => {
        assert.match(url, /\/api\/pal\/transfer$/);
        assert.equal(payload.TargetStorageKey, "world-container:palbox");
        return {
            data: {
                status: 1,
                msg: "This genetic identity already exists.",
                data: {
                    Code: "PAL_IDENTITY_CONFLICT",
                    LockedTarget: "world:pal-id",
                    Candidates: [{
                        RecordKey: "world:pal-id",
                        StorageKey: "world-container:party",
                    }],
                },
            },
        };
    };

    assert.equal(await store.movePal("world-container:palbox"), false);
    assert.equal(store.PAL_TRANSFER_CONFLICT.TargetStorageKey, "world-container:party");
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
        if (url.endsWith("/api/app-config")) return resource(appConfigFor("C:/save"));
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, "Bearer token");
            return reply(null);
        }
        if (url.endsWith("/api/session")) {
            return resource({ loaded: false, path: null, warnings: [] });
        }
        throw new Error(`Unexpected GET ${url}`);
    };

    assert.equal(await store.connectBackend(""), true);
    assert.equal(session.appState, "entry");
});

test("candidate auth failures preserve the active backend token", async () => {
    const originA = "http://10.0.0.1:58081";
    const originB = "http://10.0.0.2:58081";
    values.clear();
    localStorage.setItem("PAL_BACKEND_ORIGIN", originA);
    localStorage.setItem(backendStorageKey("PAL_AUTH_TOKEN", originA), "token-a");
    const store = newStore({ preserveStorage: true });
    axios.get = async (url, config) => {
        if (url === `${originB}/api/app-config`) {
            // The probe carries no headers at all: it only asks whether there is
            // a Pal Editor there, and the answer says there is not.
            assert.equal(config.headers, undefined);
            return resource({});
        }
        if (url === `${originA}/api/app-config`) {
            return resource(appConfigFor("C:/save-a"));
        }
        if (url === `${originA}/api/auth/auth`) {
            assert.equal(config.headers.Authorization, "Bearer token-a");
            return reply(null);
        }
        if (url === `${originA}/api/session`) {
            return resource({ loaded: false, path: null, warnings: [] });
        }
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
    assert.equal(calls[0][1], "/api/app-config");
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
        if (url.endsWith("/api/app-config")) {
            return resource(appConfigFor("C:/configured"));
        }
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, `Bearer ${expectedToken}`);
            return reply(null);
        }
        if (url.endsWith("/api/session")) {
            return resource({ loaded: false, path: null, warnings: [] });
        }
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async () => reply(null);

    let store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(session.savePath, "C:/save-a");

    expectedToken = "token-b";
    localStorage.setItem("PAL_BACKEND_ORIGIN", originB);
    store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(session.savePath, "C:/save-b");
});

test("legacy credentials and paths stay in same-origin mode", async () => {
    values.clear();
    localStorage.setItem("PAL_AUTH_TOKEN", "legacy-token");
    localStorage.setItem("PAL_GAME_SAVE_PATH", "C:/legacy-save");
    axios.get = async (url, config) => {
        if (url.endsWith("/api/app-config")) {
            return resource(appConfigFor("C:/configured"));
        }
        if (url.endsWith("/auth")) {
            assert.equal(config.headers.Authorization, "Bearer legacy-token");
            return reply(null);
        }
        if (url.endsWith("/api/session")) {
            return resource({ loaded: false, path: null, warnings: [] });
        }
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async () => reply(null);

    const store = newStore({ preserveStorage: true });
    await store.bootstrap();
    assert.equal(session.savePath, "C:/legacy-save");

    localStorage.setItem("PAL_BACKEND_ORIGIN", "http://10.0.0.2:58081");
    const remoteStore = newStore({ preserveStorage: true });
    await remoteStore.bootstrap();
    assert.equal(session.savePath, "C:/configured");
});

test("connectBackend is unavailable while editing", async () => {
    const store = newStore();
    const calls = mockBackend({ password: false, loaded: true });
    await store.bootstrap();

    assert.equal(session.appState, "editor");
    assert.equal(await store.connectBackend("10.0.0.2:58081"), false);
    // The catalogs are the last thing bootstrap reads, and they go out together,
    // so which of the five answers last is not this test's business -- that no
    // sixth request was made to the refused backend is.
    assert.match(calls.at(-1)[1], /^\/api\/catalogs\//);
});

test("bootstrap asks for a password when no remembered token exists", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true });

    await store.bootstrap();

    assert.equal(session.appState, "auth-required");
    assert.deepEqual(calls, [["GET", "/api/app-config"]]);
});

test("bootstrap resumes an already loaded backend save with a remembered token", async () => {
    const store = newStore();
    localStorage.setItem("PAL_AUTH_TOKEN", "remembered");
    const calls = mockBackend({ password: true, loaded: true });

    await store.bootstrap();

    assert.equal(session.appState, "editor");
    assert.equal(session.session.loaded, true);
    assert.equal(session.writeBackPath, "C:/save");
    assert.ok(calls.some(call => call[1] === "/api/auth/auth"));
    assert.ok(calls.some(call => call[0] === "GET" && call[1] === "/api/session"));
    // Reading the session is not loading one: a save already open is resumed,
    // never re-read from disk.
    assert.equal(calls.some(call => call[0] === "PUT"), false);
});

test("bootstrap logs in without a password and routes an empty backend to entry", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: false });

    await store.bootstrap();

    assert.equal(session.appState, "entry");
    assert.equal(session.session.loaded, false);
});

test("unlock stores only remembered tokens and resumes backend state", async () => {
    const store = newStore();
    mockBackend({ password: true, loaded: false });
    await store.bootstrap();

    await store.unlock("secret", true);

    assert.equal(localStorage.getItem("PAL_AUTH_TOKEN"), "token");
    assert.equal(session.appState, "entry");
});

test("startup network failures route to the dedicated backend error state", async () => {
    const store = newStore();
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    await store.bootstrap();

    assert.equal(session.appState, "backend-error");
    assert.equal(store.BACKEND_ERROR.message, "Network Error");
});

test("runtime failures preserve editor state", async () => {
    const store = newStore();
    const calls = mockBackend({ password: false, loaded: true });
    await store.bootstrap();
    assert.equal(session.appState, "editor");

    axios.get = async url => {
        calls.push(["GET", url]);
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };
    await store.loadLatestRelease();
    assert.equal(session.appState, "editor");
    assert.equal(session.editorOpen, true);
});

test("a failed Pal detail request preserves the current complete selection", async () => {
    const store = newStore();
    const current = detail({ InstanceId: "pal-current" });
    pals.applyDetail(current);
    pals.upsertSummaries([summary({ InstanceId: "pal-next" })]);
    pals.selectedRecordKey = current.recordKey;
    axios.get = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    assert.equal(await store.selectPal("world:pal-next"), false);
    assert.equal(store.BACKEND_ERROR.kind, "connection");
    assert.equal(pals.selectedRecordKey, current.recordKey);
    assert.equal(pals.selectedPal.InstanceId, "pal-current");
    assert.equal(session.operationPending, false);
});

test("a failed path-picker request does not clear the current save path", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: false });
    await store.bootstrap();
    assert.equal(session.savePath, "C:/save");

    const fail = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };
    axios.get = fail;
    await store.openFilePicker();

    assert.equal(session.savePath, "C:/save");
    assert.equal(session.appState, "entry");
});

test("a transient post-login failure can reuse the in-memory session token", async () => {
    const store = newStore();
    const calls = mockBackend({ password: true, loaded: false });
    await store.bootstrap();

    const backendGet = axios.get;
    let failStatus = true;
    axios.get = async url => {
        if (url.endsWith("/api/session") && failStatus) {
            failStatus = false;
            const error = new Error("Network Error");
            error.request = {};
            throw error;
        }
        return backendGet(url);
    };

    await store.unlock("secret", false);
    assert.equal(session.appState, "backend-error");

    await store.bootstrap();
    assert.equal(session.appState, "entry");
    assert.equal(calls.filter(call => call[1] === "/api/auth/login").length, 1);
});

test("startup stays connecting until loaded-save hydration completes", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: true });
    const backendGet = axios.get;
    let releasePlayers;
    axios.get = (url, config) => url.endsWith("/api/players")
        ? new Promise(resolve => { releasePlayers = () => resolve(resource([])); })
        : backendGet(url, config);

    const boot = store.bootstrap();
    while (!releasePlayers) await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(session.appState, "connecting");
    assert.equal(session.editorOpen, false);

    releasePlayers();
    await boot;
    assert.equal(session.appState, "editor");
});

test("mid-hydration authentication failure unlocks the password form", async () => {
    const store = newStore();
    mockBackend({ password: false, loaded: true });
    const backendGet = axios.get;
    axios.get = async (url, config) => {
        if (url.endsWith("/api/players")) {
            const error = new Error("Unauthorized");
            error.response = {
                status: 401,
                statusText: "Unauthorized",
                data: { msg: "Token expired" },
            };
            throw error;
        }
        return backendGet(url, config);
    };

    await store.bootstrap();

    assert.equal(session.appState, "auth-required");
    assert.equal(session.operationPending, false);
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

    assert.equal(session.appState, "backend-error");
    assert.equal(session.operationPending, false);
});

test("loaded-save hydration opens base camp editing after reloading", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        hasWorkingPal: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{ InstanceId: "pal-1" }],
    });

    await store.bootstrap();
    assert.equal(rosters.activeRosterKey, "base-workers");
    assert.equal(rosters.activePlayerUid, null);
    assert.equal(pals.selectedRecordKey, null);
    assert.equal(players.showPlayerEditor, false);

    await store.loadSave();
    assert.equal(rosters.activeRosterKey, "base-workers");
    assert.equal(rosters.activePlayerUid, null);
    assert.equal(pals.selectedRecordKey, null);
    assert.equal(players.showPlayerEditor, false);
});

test("loaded-save hydration opens player editing when there is no base camp", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{ InstanceId: "pal-1" }],
    });

    await store.bootstrap();
    assert.equal(rosters.activeRosterKey, "player:player-1");
    assert.equal(rosters.activePlayerUid, "player-1");
    assert.equal(pals.selectedRecordKey, null);
    assert.equal(players.showPlayerEditor, true);

    await store.loadSave();
    assert.equal(rosters.activeRosterKey, "player:player-1");
    assert.equal(rosters.activePlayerUid, "player-1");
    assert.equal(pals.selectedRecordKey, null);
    assert.equal(players.showPlayerEditor, true);
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
    await store.selectPal("world:pal-1");

    assert.equal(pals.selectedPal.FamilyID, "Anubis");
});

test("an edit marks the Pal it changed, and a save load forgets the marks", async () => {
    const store = newStore();
    mockBackend({
        password: false,
        loaded: true,
        players: [{ InstanceId: "player-1", NickName: "Player One" }],
        pals: [{ InstanceId: "pal-1" }],
    });

    await store.bootstrap();
    await store.selectPal("world:pal-1");
    await store.updatePal({ target: { name: "NickName", value: "Edited" } });

    // `changeState` is the backend's answer and the only edited marker there is.
    assert.equal(pals.selectedPal.changeState, "modified");
    rosters.editedOnly = true;
    rosters.createdOnly = true;

    await store.loadSave();

    // A reload is a new session, so the backend calls the same Pal unchanged and
    // nothing on this side remembers otherwise.
    assert.equal(pals.summary("world:pal-1").changeState, "unchanged");
    assert.equal(rosters.editedOnly, false);
    assert.equal(rosters.createdOnly, false);
});

test("the app config publishes backend locales and switches to the translated locale", async () => {
    const store = newStore();
    const locales = {
        en: "English",
        de: "Deutsch",
        "zh-TW": "繁體中文",
    };
    mockBackend({ password: false, locale: "de", locales });

    await store.bootstrap();

    assert.deepEqual(appState.localeOptions, locales);
    assert.equal(appState.locale, "de");
    assert.equal(store.getTranslatedText("BackendError_Title"), "Etwas ist schiefgelaufen");
});

test("language changes refresh only the active roster and re-fetch others lazily", async () => {
    const store = newStore();
    store.IS_LOCKED = false;
    session.appState = "editor";
    rosters.rosters = [
        { rosterKey: "player:player-1", kind: "player", label: "One", playerUid: "player-1" },
        { rosterKey: "global-palbox", kind: "global_palbox", label: "GPS", playerUid: null },
    ];
    rosters.recordKeysByRoster.set("player:player-1", []);
    rosters.recordKeysByRoster.set("global-palbox", []);
    rosters.activeRosterKey = "player:player-1";

    const requestedRosters = [];
    axios.patch = async url => {
        assert.equal(url, "/api/app-config");
        return resource(appConfigFor("C:/save"));
    };
    axios.get = async url => {
        const rosterPals = url.match(/\/api\/rosters\/([^/]+)\/pals$/);
        if (rosterPals) {
            const rosterKey = decodeURIComponent(rosterPals[1]);
            requestedRosters.push(rosterKey);
            return resource(rosterKey === "global-palbox"
                ? [summary({
                    InstanceId: "gps-pal",
                    recordKey: "gps:0",
                    DisplayName: "Translated GPS Pal",
                })]
                : []);
        }
        if (url.includes("/api/catalogs/")) return resource(emptyCatalog(url));
        throw new Error(`Unexpected GET ${url}`);
    };

    assert.equal(await store.updateI18n(), true);
    // Only the roster currently being viewed is refreshed eagerly; every other
    // roster's keys are dropped instead of being fetched all at once.
    assert.deepEqual(requestedRosters, ["player:player-1"]);

    // A different roster re-fetches in the new language once it is selected.
    await store.selectPlayer("global-palbox");
    assert.deepEqual(requestedRosters, ["player:player-1", "global-palbox"]);
    assert.equal(pals.summary("gps:0").DisplayName, "Translated GPS Pal");
});

test("language changes fail when the active roster cannot be refreshed", async () => {
    const store = newStore();
    store.IS_LOCKED = false;
    session.appState = "editor";
    rosters.activeRosterKey = "global-palbox";
    rosters.recordKeysByRoster.set("global-palbox", []);

    let staticRequests = 0;
    axios.patch = async () => reply(null);
    axios.get = async url => {
        if (url.match(/\/api\/rosters\/([^/]+)\/pals$/)) {
            const error = new Error("Server Error");
            error.response = {
                status: 500,
                statusText: "Server Error",
                data: { error: { code: "UNEXPECTED_ERROR", message: "GPS refresh failed" } },
            };
            throw error;
        }
        staticRequests += 1;
        return reply({ dict: {}, arr: [] });
    };

    assert.equal(await store.updateI18n(), false);
    assert.equal(staticRequests, 0);
    assert.equal(session.operationPending, false);
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
    assert.equal(pals.selectedRecordKey, null);
    await store.healAllPals();

    // No Pal and no roster in the request: healing everything asks for nothing to
    // be selected first, and the reply names the lists to redraw.
    assert.deepEqual(
        calls.filter(call => call[1].endsWith("/api/pal-heals")),
        [["POST", "/api/pal-heals"]],
    );
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

    assert.equal(session.appState, "auth-required");
    assert.equal(store.AUTH_MESSAGE_KEY, "AuthView_Wrong_Password");
});

test("expired sessions retain an inline authentication explanation", () => {
    const store = newStore();

    store.requireAuth("AuthView_Session_Expired");

    assert.equal(session.appState, "auth-required");
    assert.equal(store.AUTH_MESSAGE_KEY, "AuthView_Session_Expired");
});

test("missing player validation uses a nonblocking warning", async () => {
    const store = newStore();

    await store.updatePlayer({ target: { name: "Rank", value: 1 } });

    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Select_Player");
    assert.equal(store.CURRENT_MESSAGE.severity, "warning");
    assert.equal(store.CURRENT_MESSAGE.presentation, "toast");
    assert.equal(session.operationPending, false);
});

// A player the editor has open, so the write actions have somewhere to write.
function openPlayer(overrides = {}) {
    const player = {
        InstanceId: "player-1",
        NickName: "Tester",
        Level: 10,
        UnlockedRecipeTechnologyNames: ["Workbench"],
        ...overrides,
    };
    players.playersByUid = new Map([["player-1", player]]);
    rosters.activeRosterKey = "player:player-1";
    return player;
}

test("a field edit patches the player resource and keeps the answer", async () => {
    const store = newStore();
    openPlayer();
    const calls = [];
    axios.patch = async (url, body) => {
        calls.push([url, body]);
        return resource({ InstanceId: "player-1", NickName: "Renamed" });
    };

    await store.updatePlayer({ target: { name: "NickName", value: "Renamed" } });

    // One request, not a PATCH followed by a read: the PATCH answers with the
    // player, and that answer is what the panel now shows.
    assert.deepEqual(calls, [["/api/players/player-1", { NickName: "Renamed" }]]);
    assert.equal(players.selectedPlayer.NickName, "Renamed");
});

test("unlocking every technology can never lock one", async () => {
    const store = newStore();
    openPlayer({ UnlockedRecipeTechnologyNames: ["OwnedByTheSaveOnly"] });
    // The catalog is what "all" means, and it does not have to contain
    // everything the save does.
    useCatalogsStore().technologiesByLevel = { 1: [{ InternalName: "Workbench" }] };
    let sent;
    axios.patch = async (url, body) => {
        sent = body.UnlockedRecipeTechnologyNames;
        return resource({ InstanceId: "player-1" });
    };

    await store.unlockAllTechs();

    assert.deepEqual(sent, ["OwnedByTheSaveOnly", "Workbench"]);
});

test("locking a technology matches the spelling the save uses", async () => {
    const store = newStore();
    openPlayer({ UnlockedRecipeTechnologyNames: ["workbench", "PalCondenser"] });
    let sent;
    axios.patch = async (url, body) => {
        sent = body.UnlockedRecipeTechnologyNames;
        return resource({ InstanceId: "player-1" });
    };

    await store.toggleTech("Workbench", false);

    assert.deepEqual(sent, ["PalCondenser"]);
});

test("editing an inventory slot needs no second request to redraw the grid", async () => {
    const store = newStore();
    openPlayer();
    const calls = [];
    const inventory = { containers: { food: { slots: [] } }, warnings: [] };
    axios.patch = async (url, body) => {
        calls.push([url, body]);
        return resource(inventory);
    };

    assert.equal(await store.patchInventorySlot("food", 3, "Curry", 42), true);

    assert.deepEqual(calls, [[
        "/api/players/player-1/inventory/3",
        { containerKind: "food", itemId: "Curry", count: 42, allowOverstack: false },
    ]]);
    assert.deepEqual(players.inventory, inventory);
});

test("unexpected request errors release loading before showing details", async t => {
    const store = newStore();
    const originalConsoleError = console.error;
    console.error = () => {};
    t.after(() => { console.error = originalConsoleError; });
    axios.post = async () => { throw new TypeError("broken request adapter"); };

    await store.writeSave();

    assert.equal(session.operationPending, false);
    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Unexpected_Frontend_Error");
    assert.match(store.CURRENT_MESSAGE.log, /broken request adapter/);
});

test("one gate covers the whole app and is released even when an operation fails", async t => {
    const app = await readFile(new URL("../src/App.vue", import.meta.url), "utf8");
    // Spec 8.8 wants one region made inert, not a `:disabled` on each control:
    // that is what makes a control added later covered without being told to be.
    assert.match(app, /:inert="interactionBlocked \|\| undefined"/);
    assert.match(app, /interactionBlocked = computed\(\(\) => modalOverlay\.value \|\| sessionStore\.operationPending\)/);

    const store = newStore();
    mockBackend({ password: false });
    const originalConsoleError = console.error;
    console.error = () => {};
    t.after(() => { console.error = originalConsoleError; });

    let pendingDuringRequest = null;
    axios.get = async () => {
        pendingDuringRequest = session.operationPending;
        throw new TypeError("broken request adapter");
    };

    await store.loadLatestRelease();

    assert.equal(pendingDuringRequest, true);
    // Released by `finally`, so a failure cannot leave the app inert forever.
    assert.equal(session.operationPending, false);
});

test("a failed donation dismissal is reported as an operation error", async () => {
    // Whether the panel opens is now a field of the app config, not a request of
    // its own -- what can still fail is remembering that it was dismissed.
    const store = newStore();
    axios.patch = async () => {
        const error = new Error("Network Error");
        error.request = {};
        throw error;
    };

    await store.shownDonate();

    assert.equal(store.BACKEND_ERROR.kind, "connection");
});

test("successful saves use a nonblocking success message", async () => {
    const store = newStore();
    axios.post = async url => {
        assert.equal(url, "/api/save/save");
        return reply(null);
    };
    session.writeBackPath = "C:/output";

    await store.writeSave();

    assert.equal(store.CURRENT_MESSAGE.messageKey, "Message_Save_Success");
    assert.deepEqual(store.CURRENT_MESSAGE.args, ["C:/output"]);
    assert.equal(store.CURRENT_MESSAGE.severity, "success");
    assert.equal(store.CURRENT_MESSAGE.presentation, "toast");
});

test("deleting the last Pal falls through to the player editor instead of a blank canvas", async () => {
    const store = newStore();
    players.playersByUid.set("player-1", { InstanceId: "player-1", NickName: "Player One" });
    rosters.activeRosterKey = "player:player-1";
    rosters.recordKeysByRoster.set("player:player-1", ["world:pal-1"]);
    pals.applyDetail(detail({ InstanceId: "pal-1" }));
    pals.selectedRecordKey = "world:pal-1";

    axios.delete = async () => reply(null);
    axios.get = async url => {
        if (url.endsWith("/api/pal/containers")) return reply([]);
        if (url.match(/\/api\/rosters\/([^/]+)\/pals$/)) return resource([]);
        throw new Error(`Unexpected GET ${url}`);
    };

    await store.delPal();

    assert.equal(pals.selectedRecordKey, null);
    assert.equal(rosters.activePlayerUid, "player-1");
    assert.equal(players.selectedPlayer.InstanceId, "player-1");
    assert.equal(players.showPlayerEditor, true);
});

test("exporting a Pal to the Global Palbox auto-jumps to its new location and refreshes only affected rosters", async () => {
    const store = newStore();
    players.playersByUid.set("player-1", { InstanceId: "player-1", NickName: "Player One" });
    const targetStorageKey = "gps-global";
    store.PAL_CONTAINERS = [
        { StorageKey: targetStorageKey, StorageKind: "global_palbox", ContainerKind: "global" },
        { StorageKey: "world-container:palbox", StorageKind: "world", ContainerKind: "storage", OwnerPlayerUId: "player-1" },
    ];
    rosters.activeRosterKey = "player:player-1";
    rosters.recordKeysByRoster.set("player:player-1", ["world:pal-1"]);
    pals.applyDetail(detail({ InstanceId: "pal-1", OwnerPlayerUId: "player-1" }));
    pals.selectedRecordKey = "world:pal-1";

    const requestedRosters = [];
    axios.get = async url => {
        if (url.endsWith("/api/pal/containers")) return reply(store.PAL_CONTAINERS);
        const rosterPals = url.match(/\/api\/rosters\/([^/]+)\/pals$/);
        if (rosterPals) {
            const rosterKey = decodeURIComponent(rosterPals[1]);
            requestedRosters.push(rosterKey);
            return resource(rosterKey === "global-palbox"
                ? [summary({ InstanceId: "pal-1", recordKey: "gps:pal-1" })]
                : []);
        }
        if (url.match(/\/api\/pals\/(.+)$/)) {
            return resource(detail({ InstanceId: "pal-1", recordKey: "gps:pal-1" }));
        }
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async url => {
        if (url.endsWith("/api/pal/transfer")) return reply({ RecordKey: "gps:pal-1" });
        throw new Error(`Unexpected POST ${url}`);
    };

    assert.equal(await store.movePal(targetStorageKey), true);
    // Only the source roster and the Global Palbox are refreshed, not every player.
    assert.deepEqual(requestedRosters, ["player:player-1", "global-palbox"]);
    // Auto-jumped to the Global Palbox and selected the newly exported Pal.
    assert.equal(rosters.activeRosterKey, "global-palbox");
    assert.equal(pals.selectedRecordKey, "gps:pal-1");
});

test("resolving an update conflict auto-jumps to the updated Pal's new location", async () => {
    const store = newStore();
    players.playersByUid.set("player-1", { InstanceId: "player-1", NickName: "Player One" });
    store.PAL_CONTAINERS = [
        { StorageKey: "world-container:palbox", StorageKind: "world", ContainerKind: "storage", OwnerPlayerUId: "player-1" },
    ];
    // Looking at the Global Palbox, updating a Pal into player-1's storage.
    rosters.activeRosterKey = "global-palbox";
    rosters.recordKeysByRoster.set("global-palbox", []);
    store.PAL_TRANSFER_CONFLICT = {
        SourceRecordKey: "gps:0",
        TargetStorageKey: "world-container:palbox",
        LockedTarget: "world:pal-1",
        Candidates: [{
            RecordKey: "world:pal-1",
            StorageKind: "world",
            OwnerPlayerUId: "player-1",
        }],
    };

    const requestedRosters = [];
    axios.get = async url => {
        if (url.endsWith("/api/pal/containers")) return reply(store.PAL_CONTAINERS);
        const rosterPals = url.match(/\/api\/rosters\/([^/]+)\/pals$/);
        if (rosterPals) {
            const rosterKey = decodeURIComponent(rosterPals[1]);
            requestedRosters.push(rosterKey);
            return resource(rosterKey === "player:player-1"
                ? [summary({ InstanceId: "pal-1" })]
                : []);
        }
        if (url.match(/\/api\/pals\/(.+)$/)) return resource(detail({ InstanceId: "pal-1" }));
        throw new Error(`Unexpected GET ${url}`);
    };
    axios.post = async url => {
        if (url.endsWith("/api/pal/transfer")) return reply(null);
        throw new Error(`Unexpected POST ${url}`);
    };

    assert.equal(await store.updateConflictingPal(), true);
    // The affected rosters are refreshed (active + target), not every player.
    assert.deepEqual(requestedRosters, ["global-palbox", "player:player-1"]);
    // Auto-jumped to the player and selected the updated Pal.
    assert.equal(rosters.activeRosterKey, "player:player-1");
    assert.equal(pals.selectedRecordKey, "world:pal-1");
});
