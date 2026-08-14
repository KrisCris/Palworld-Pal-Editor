import assert from "node:assert/strict";
import test from "node:test";

import * as backendConnection from "../src/services/backend-connection.js";

const {
    backendStorageKey,
    backendUrl,
    normalizeBackendOrigin,
    readRecentBackends,
    readStorage,
    rememberBackend,
    removeStorage,
    writeStorage,
} = backendConnection;

const storage = () => {
    const values = new Map();
    return {
        getItem: key => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value),
        removeItem: key => values.delete(key),
    };
};

test("normalizes backend origins and builds backend URLs", () => {
    assert.equal(normalizeBackendOrigin("", "http://127.0.0.1:58080"), "");
    assert.equal(normalizeBackendOrigin("http://127.0.0.1:58080", "http://127.0.0.1:58080"), "");
    assert.equal(normalizeBackendOrigin("127.0.0.1:58081", "http://127.0.0.1:58080"), "http://127.0.0.1:58081");
    assert.equal(normalizeBackendOrigin("https://example.test:8443/", "http://127.0.0.1:58080"), "https://example.test:8443");
    assert.throws(() => normalizeBackendOrigin("ftp://example.test", "http://127.0.0.1:58080"), /HTTP/);
    assert.throws(() => normalizeBackendOrigin("http://user@example.test", "http://127.0.0.1:58080"), /credentials/);
    assert.throws(() => normalizeBackendOrigin("http://example.test/api", "http://127.0.0.1:58080"), /origin/);
    assert.equal(backendUrl("", "/api/save/status"), "/api/save/status");
    assert.equal(backendUrl("http://10.0.0.2:58080", "/image/ui/heal"), "http://10.0.0.2:58080/image/ui/heal");
});

test("versions backend images with the first six Git hash characters", () => {
    assert.equal(typeof backendConnection.versionedBackendAssetUrl, "function");
    assert.equal(
        backendConnection.versionedBackendAssetUrl(
            "http://10.0.0.2:58080",
            "/image/ui/heal",
            "1.0.0-NIGHTLY-a1b2c3d-KrisCris/Palworld-Pal-Editor-20260814",
        ),
        "http://10.0.0.2:58080/image/ui/heal?v=a1b2c3",
    );
    assert.equal(
        backendConnection.versionedBackendAssetUrl("", "/image/ui/heal", "1.0.0-RELEASE-ABCDEF1"),
        "/image/ui/heal?v=abcdef",
    );
});

test("leaves backend images unversioned when the Git hash cannot be extracted", () => {
    assert.equal(typeof backendConnection.versionedBackendAssetUrl, "function");
    for (const version of ["development", "0.0.0", "1.0.0-NIGHTLY-not-a-hash-repo-time", "", undefined]) {
        assert.equal(
            backendConnection.versionedBackendAssetUrl("http://10.0.0.2:58080", "/image/ui/heal", version),
            "http://10.0.0.2:58080/image/ui/heal",
        );
    }
});

test("scopes storage values by backend and retains five recent backends", () => {
    const local = storage();
    assert.notEqual(backendStorageKey("PAL_AUTH_TOKEN", ""), backendStorageKey("PAL_AUTH_TOKEN", "http://10.0.0.2:58080"));
    for (const origin of ["http://one.test", "http://two.test", "http://three.test", "http://four.test", "http://five.test"]) {
        rememberBackend(local, origin);
    }
    assert.deepEqual(rememberBackend(local, "http://six.test").length, 5);
    assert.deepEqual(readRecentBackends(local), ["http://six.test", "http://five.test", "http://four.test", "http://three.test", "http://two.test"]);
});

test("normalizes legacy recent backends and persists the deduplicated list", () => {
    const local = storage();
    local.setItem("PAL_BACKEND_RECENT", JSON.stringify([
        "http://one.test/",
        "http://one.test",
        "not a backend",
        "https://two.test/path",
        "http://three.test",
    ]));

    assert.deepEqual(readRecentBackends(local, "http://page.test"), ["http://one.test", "http://three.test"]);
    assert.equal(local.getItem("PAL_BACKEND_RECENT"), JSON.stringify(["http://one.test", "http://three.test"]));
});

test("storage helpers tolerate unavailable or throwing storage", () => {
    const throwing = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }, removeItem() { throw new Error("blocked"); } };
    assert.equal(readStorage(undefined, "key"), null);
    assert.equal(readStorage(throwing, "key"), null);
    assert.equal(writeStorage(undefined, "key", "value"), false);
    assert.equal(writeStorage(throwing, "key", "value"), false);
    assert.equal(removeStorage(undefined, "key"), false);
    assert.equal(removeStorage(throwing, "key"), false);
});
