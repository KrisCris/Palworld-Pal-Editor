// Guild laboratory research for the loaded save.
//
// The BaseCamp editor's data and nothing else. It keeps the payload's own field
// names: renaming them would be a rewrite of a component nothing asked to change.

import { ref } from "vue";
import { defineStore } from "pinia";

import { completeGuildResearch, getGuildResearch } from "../api/research.js";
import { useBackendStore } from "./backend.js";
import { useMessagesStore } from "./messages.js";
import { gated, useSessionStore } from "./session.js";

const EMPTY_RESEARCH = { CategoryOrder: [], Guilds: [] };

export const useResearchStore = defineStore("research", () => {
    const backend = useBackendStore();
    const messages = useMessagesStore();
    const session = useSessionStore();

    const research = ref({ ...EMPTY_RESEARCH });
    const selectedGuildId = ref(null);

    function applyResearch(tree) {
        research.value = tree ?? { ...EMPTY_RESEARCH };
        const guilds = research.value.Guilds ?? [];
        // A guild that is no longer in the tree cannot stay selected; the first
        // one is what the editor falls back to.
        if (!guilds.some(guild => guild.GuildId === selectedGuildId.value)) {
            selectedGuildId.value = guilds[0]?.GuildId ?? null;
        }
    }

    async function load() {
        const epoch = session.sessionEpoch;
        let tree;
        try {
            tree = await getGuildResearch(session.readOptions());
        } catch (error) {
            backend.reportApiFailure(error, "Operation_BaseCamp_Research");
            return false;
        }
        if (!session.isCurrentSession(epoch)) return false;
        applyResearch(tree);
        return true;
    }

    // `scope` is one of `{researchId}`, `{category}` or `{all: true}`. The reply
    // says how many rows moved, which is the only thing that tells the user
    // anything -- completing a category that was already complete looks exactly
    // like completing one that was not.
    async function complete(scope) {
        if (!selectedGuildId.value) return false;
        let result;
        try {
            result = await completeGuildResearch(selectedGuildId.value, scope);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_BaseCamp_Research");
            return false;
        }
        applyResearch(result.research);
        messages.showToast("Message_BaseCamp_Research_Completed", "success", [result.changed]);
        return true;
    }

    function clear() {
        research.value = { ...EMPTY_RESEARCH };
        selectedGuildId.value = null;
    }

    return {
        research,
        selectedGuildId,
        clear,

        ...gated(session, { load, complete }),
    };
});
