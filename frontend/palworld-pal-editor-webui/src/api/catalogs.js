// The game's own data, which no save can change (spec §8.4).
//
// Five reads that need no session, so unlike every other client here they take
// no epoch and are never aborted: their answer is as good after a reload as
// before one.

import { request } from "./http.js";

export function getPalCatalog(options) {
    return request("get", "/api/catalogs/pals", options);
}

export function getSkillCatalog(options) {
    return request("get", "/api/catalogs/skills", options);
}

export function getItemCatalog(options) {
    return request("get", "/api/catalogs/items", options);
}

export function getTechnologyCatalog(options) {
    return request("get", "/api/catalogs/technologies", options);
}

export function getSkinCatalog(options) {
    return request("get", "/api/catalogs/skins", options);
}
