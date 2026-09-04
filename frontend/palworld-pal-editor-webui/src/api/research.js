// Guild laboratory research.
//
// One resource for the whole save. The tree keeps the field names the BaseCamp
// editor already reads -- the casing rule is about how a Pal says where it is.

import { request } from "./http.js";

export function getGuildResearch(options) {
    return request("get", "/api/guild-research", options);
}

// `scope` names exactly one of `researchId`, `category` or `all`, and the reply
// is `{changed, research}` -- the row count is the one thing the new tree cannot
// say about itself.
export function completeGuildResearch(guildId, scope, options) {
    return request(
        "patch",
        `/api/guild-research/${encodeURIComponent(guildId)}`,
        { ...options, body: scope },
    );
}
