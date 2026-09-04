// Saved Pal and skill templates.
//
// Templates outlive a save: they are stored in the app's config, not in the file
// being edited, so nothing here is dropped when a session ends. Each entry is
// whatever the API returned -- a summary of the Pal, or one skill group -- and
// never the raw Pal data behind it, which only the backend ever reads.
//
// Applying a skill template is not here: it changes a Pal, so it is a Pal write
// and lives in `stores/pals` with the rest of them.

import { ref } from "vue";
import { defineStore } from "pinia";

import {
    createPalTemplate,
    createSkillTemplate,
    deletePalTemplate,
    deleteSkillTemplate,
    listPalTemplates,
    listSkillTemplates,
    renameSkillTemplate,
} from "../api/templates.js";

export const useTemplatesStore = defineStore("templates", () => {
    const palTemplates = ref([]);
    const skillTemplates = ref([]);

    const without = (templates, templateId) => templates.filter(
        template => template.templateId !== templateId,
    );

    async function loadPalTemplates() {
        palTemplates.value = await listPalTemplates();
    }

    async function savePalTemplate(name, recordKey) {
        palTemplates.value = [...palTemplates.value, await createPalTemplate(name, recordKey)];
    }

    async function removePalTemplate(templateId) {
        await deletePalTemplate(templateId);
        palTemplates.value = without(palTemplates.value, templateId);
    }

    async function loadSkillTemplates() {
        skillTemplates.value = await listSkillTemplates();
    }

    async function saveSkillTemplate(name, type, recordKey) {
        skillTemplates.value = [
            ...skillTemplates.value,
            await createSkillTemplate(name, type, recordKey),
        ];
    }

    async function renameTemplate(templateId, name) {
        const renamed = await renameSkillTemplate(templateId, name);
        skillTemplates.value = skillTemplates.value.map(
            template => template.templateId === templateId ? renamed : template,
        );
    }

    async function removeSkillTemplate(templateId) {
        await deleteSkillTemplate(templateId);
        skillTemplates.value = without(skillTemplates.value, templateId);
    }

    function clear() {
        palTemplates.value = [];
        skillTemplates.value = [];
    }

    return {
        palTemplates,
        skillTemplates,
        loadPalTemplates,
        savePalTemplate,
        removePalTemplate,
        loadSkillTemplates,
        saveSkillTemplate,
        renameTemplate,
        removeSkillTemplate,
        clear,
    };
});
