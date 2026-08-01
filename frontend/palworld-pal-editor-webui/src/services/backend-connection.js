const MAX_RECENT = 5;
const RECENT_KEY = "PAL_BACKEND_RECENT";

export function normalizeBackendOrigin(input, frontendOrigin) {
    if (!input.trim()) return "";
    const url = new URL(/^[a-z][a-z\d+.-]*:/i.test(input) ? input : `http://${input}`);
    if (!/^https?:$/.test(url.protocol)) throw new Error("Backend must use HTTP or HTTPS");
    if (url.username || url.password) throw new Error("Backend origin cannot include credentials");
    if (url.pathname !== "/" || url.search || url.hash) throw new Error("Backend must be an origin");
    return url.origin === new URL(frontendOrigin).origin ? "" : url.origin;
}

export function backendUrl(origin, path) {
    return origin ? new URL(path, `${origin}/`).href : path;
}

export function backendStorageKey(name, origin) {
    return origin ? `${name}:${encodeURIComponent(origin)}` : name;
}

export function readStorage(storage, key) {
    try { return storage?.getItem(key) ?? null; }
    catch { return null; }
}

export function writeStorage(storage, key, value) {
    try { storage?.setItem(key, value); return !!storage; }
    catch { return false; }
}

export function removeStorage(storage, key) {
    try { storage?.removeItem(key); return !!storage; }
    catch { return false; }
}

export function readRecentBackends(storage, frontendOrigin = globalThis.location?.origin || "http://localhost") {
    try {
        const recent = JSON.parse(readStorage(storage, RECENT_KEY) || "[]");
        if (!Array.isArray(recent)) return [];
        const normalized = [...new Set(recent.flatMap(item => {
            try {
                const origin = normalizeBackendOrigin(item, frontendOrigin);
                return origin ? [origin] : [];
            } catch { return []; }
        }))].slice(0, MAX_RECENT);
        if (JSON.stringify(recent) !== JSON.stringify(normalized)) writeStorage(storage, RECENT_KEY, JSON.stringify(normalized));
        return normalized;
    } catch { return []; }
}

export function rememberBackend(storage, origin) {
    const recent = [origin, ...readRecentBackends(storage).filter(item => item !== origin)].slice(0, MAX_RECENT);
    writeStorage(storage, RECENT_KEY, JSON.stringify(recent));
    return recent;
}
