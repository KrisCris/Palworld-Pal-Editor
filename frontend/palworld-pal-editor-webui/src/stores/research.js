// Guild laboratory research for the loaded save (spec §10).
//
// The BaseCamp editor's data and nothing else. It keeps the payload's own field
// names: renaming them would be a rewrite of a component §8.6 says not to change.

import { ref } from "vue";
import { defineStore } from "pinia";

import { completeGuildResearch, getGuildResearch } from "../api/research.js";
import { useSessionStore } from "./session.js";

const EMPTY_RESEARCH = { CategoryOrder: [], Guilds: [] };

export const useResearchStore = defineStore("research", () => {
    const session = useSessionStore();

    const research = ref({ ...EMPTY_RESEARCH });
    const selectedGuildId = ref(null);

    function applyResearch(tree) {
        research.value = tree ?? { ...EMPTY_RESEARCH };
        const guilds = research.value.Guilds ?? [];
        // A guild that is no longer in the tree cannot stay selected; the first
        // one is what the editor opened on before this store existed.
        if (!guilds.some(guild => guild.GuildId === selectedGuildId.value)) {
            selectedGuildId.value = guilds[0]?.GuildId ?? null;
        }
    }

    async function load() {
        const epoch = session.sessionEpoch;
        const tree = await getGuildResearch(session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        applyResearch(tree);
        return true;
    }

    // `scope` is one of `{researchId}`, `{category}` or `{all: true}`. Answers
    // with how many rows moved, which is what the UI reports back to the user.
    async function complete(scope) {
        if (!selectedGuildId.value) return null;
        const result = await completeGuildResearch(selectedGuildId.value, scope);
        applyResearch(result.research);
        return result.changed;
    }

    function clear() {
        research.value = { ...EMPTY_RESEARCH };
        selectedGuildId.value = null;
    }

    return { research, selectedGuildId, load, complete, clear };
});
