// The read-only game catalogs.
//
// Pal species, skills, items, technologies and skins. None of it belongs to a
// save, so nothing here is cleared when one is closed -- but the localized names
// do belong to a language, which is why `load()` runs again after the locale
// changes rather than only at startup.
//
// The backend sends each catalog as a list. The `...ByName` maps are built here,
// from that same list, so there is one copy of every row and no way for an index
// to disagree with what it indexes.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
    getItemCatalog,
    getPalCatalog,
    getSkillCatalog,
    getSkinCatalog,
    getTechnologyCatalog,
} from "../api/catalogs.js";
import { elementIconKey } from "../pal-traits.js";

const byInternalName = rows => Object.fromEntries(
    rows.map(row => [row.InternalName, row]),
);

export const useCatalogsStore = defineStore("catalogs", () => {
    const pals = ref([]);
    const items = ref([]);
    const passiveSkills = ref([]);
    const activeSkills = ref([]);
    const skins = ref([]);
    const technologiesByLevel = ref({});

    const palsByName = computed(() => byInternalName(pals.value));
    const itemsByName = computed(() => byInternalName(items.value));
    const passiveSkillsByName = computed(() => byInternalName(passiveSkills.value));
    const activeSkillsByName = computed(() => byInternalName(activeSkills.value));

    // Which element icons a species is drawn with. The species is the catalog's
    // to answer for; the icon each element maps to is `pal-traits`.
    const palElementKeys = dataAccessKey => (palsByName.value[dataAccessKey]?.Elements ?? [])
        .map(elementIconKey)
        .filter(Boolean);

    // Five independent reads, so they go out together. The first failure rejects
    // for all of them, which is what the caller wants: a half-loaded catalog is
    // an editor that silently offers the wrong choices.
    async function load() {
        const [palCatalog, skillCatalog, itemCatalog, techCatalog, skinCatalog] =
            await Promise.all([
                getPalCatalog(),
                getSkillCatalog(),
                getItemCatalog(),
                getTechnologyCatalog(),
                getSkinCatalog(),
            ]);
        pals.value = palCatalog.pals;
        passiveSkills.value = skillCatalog.passive;
        activeSkills.value = skillCatalog.active;
        items.value = itemCatalog.items;
        technologiesByLevel.value = techCatalog.byLevel;
        skins.value = skinCatalog.skins;
    }

    return {
        pals,
        palsByName,
        items,
        itemsByName,
        passiveSkills,
        passiveSkillsByName,
        activeSkills,
        activeSkillsByName,
        skins,
        technologiesByLevel,
        palElementKeys,
        load,
    };
});
