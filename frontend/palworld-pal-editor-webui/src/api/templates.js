// Pal and skill template resources.
//
// Templates are the one thing this API stores outside the save, so they survive a
// session and are addressed by `templateId` rather than by anything in the save.
// A Pal template holds a whole Pal; a skill template holds one skill group.
//
// Applying a skill template is a Pal write, not a template read: it answers with
// the same operation result every other Pal write does, which is why it is
// addressed to the Pal.

import { request } from "./http.js";

export function listPalTemplates(options) {
    return request("get", "/api/pal-templates", options);
}

export function createPalTemplate(name, recordKey, options) {
    return request("post", "/api/pal-templates", {
        ...options,
        body: { name, recordKey },
    });
}

export function deletePalTemplate(templateId, options) {
    return request("delete", `/api/pal-templates/${encodeURIComponent(templateId)}`, options);
}

export function listSkillTemplates(options) {
    return request("get", "/api/skill-templates", options);
}

// `type` is `passive` or `active`; the Pal's current group of that kind is what
// gets saved.
export function createSkillTemplate(name, type, recordKey, options) {
    return request("post", "/api/skill-templates", {
        ...options,
        body: { name, type, recordKey },
    });
}

export function renameSkillTemplate(templateId, name, options) {
    return request("patch", `/api/skill-templates/${encodeURIComponent(templateId)}`, {
        ...options,
        body: { name },
    });
}

export function deleteSkillTemplate(templateId, options) {
    return request("delete", `/api/skill-templates/${encodeURIComponent(templateId)}`, options);
}

export function applySkillTemplate(recordKey, templateId, options) {
    return request(
        "post",
        `/api/pals/${encodeURIComponent(recordKey)}/skill-template-applications`,
        { ...options, body: { templateId } },
    );
}
