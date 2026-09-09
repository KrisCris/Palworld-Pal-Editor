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
import { useBackendStore } from "./backend.js";
import { useMessagesStore } from "./messages.js";
import { usePalsStore } from "./pals.js";
import { gated, useSessionStore } from "./session.js";

export const useTemplatesStore = defineStore("templates", () => {
    const backend = useBackendStore();
    const messages = useMessagesStore();
    const pals = usePalsStore();
    const session = useSessionStore();

    const palTemplates = ref([]);
    const skillTemplates = ref([]);

    const without = (templates, templateId) => templates.filter(
        template => template.templateId !== templateId,
    );

    // Seven operations, one shape: do it, say so if it failed, and say so if it
    // worked and the user would not otherwise see that it had.
    async function run(action, operationKey, toastKey) {
        try {
            await action();
        } catch (error) {
            backend.reportApiFailure(error, operationKey);
            return false;
        }
        if (toastKey) messages.showToast(toastKey, "success");
        return true;
    }

    function loadPalTemplates() {
        return run(
            async () => { palTemplates.value = await listPalTemplates(); },
            "Operation_Load_Pal_Templates",
        );
    }

    // A Pal template is made from the Pal that is open, so the selection is read
    // here rather than passed in by the dialog that has no other use for it.
    function savePalTemplate(name) {
        const recordKey = pals.selectedRecordKey;
        if (!recordKey) return false;
        return run(
            async () => {
                palTemplates.value = [
                    ...palTemplates.value,
                    await createPalTemplate(name, recordKey),
                ];
            },
            "Operation_Save_Pal_Template",
            "Message_Pal_Template_Saved",
        );
    }

    function removePalTemplate(templateId) {
        return run(
            async () => {
                await deletePalTemplate(templateId);
                palTemplates.value = without(palTemplates.value, templateId);
            },
            "Operation_Delete_Pal_Template",
            "Message_Pal_Template_Deleted",
        );
    }

    function loadSkillTemplates() {
        return run(
            async () => { skillTemplates.value = await listSkillTemplates(); },
            "Operation_Load_Skill_Templates",
        );
    }

    function saveSkillTemplate(type, name) {
        const recordKey = pals.selectedRecordKey;
        if (!recordKey) return false;
        return run(
            async () => {
                skillTemplates.value = [
                    ...skillTemplates.value,
                    await createSkillTemplate(name, type, recordKey),
                ];
            },
            "Operation_Save_Skill_Template",
            "Message_Skill_Template_Saved",
        );
    }

    function renameTemplate(templateId, name) {
        return run(
            async () => {
                const renamed = await renameSkillTemplate(templateId, name);
                skillTemplates.value = skillTemplates.value.map(
                    template => template.templateId === templateId ? renamed : template,
                );
            },
            "Operation_Rename_Skill_Template",
            "Message_Skill_Template_Renamed",
        );
    }

    function removeSkillTemplate(templateId) {
        return run(
            async () => {
                await deleteSkillTemplate(templateId);
                skillTemplates.value = without(skillTemplates.value, templateId);
            },
            "Operation_Delete_Skill_Template",
            "Message_Skill_Template_Deleted",
        );
    }

    function clear() {
        palTemplates.value = [];
        skillTemplates.value = [];
    }

    return {
        palTemplates,
        skillTemplates,
        clear,

        ...gated(session, {
            loadPalTemplates,
            savePalTemplate,
            removePalTemplate,
            loadSkillTemplates,
            saveSkillTemplate,
            renameTemplate,
            removeSkillTemplate,
        }),
    };
});
