// Reading a Pal for display: its element, its gender, what makes it special, and
// which of the game's skins and suitabilities apply to it.
//
// Nothing here asks the backend or holds state. These are the questions a control
// asks about a Pal it is already showing.

const ELEMENT_ALIASES = Object.freeze({
    Leaf: "Grass",
    Earth: "Ground",
    Electricity: "Electric",
    Normal: "Neutral",
});
const ELEMENT_ICON_KEYS = new Set([
    "Water", "Fire", "Dragon", "Grass", "Ground", "Ice", "Electric", "Neutral", "Dark",
]);

// The save and the catalogs do not always use the game's own name for an element,
// and there is no icon for one this does not recognise.
export function elementIconKey(element) {
    const key = ELEMENT_ALIASES[element] ?? element;
    return ELEMENT_ICON_KEYS.has(key) ? key : null;
}

export function passiveTier(rating) {
    if (rating >= 5) return "top";
    if (rating >= 4) return "high";
    if (rating >= 2) return "positive";
    if (rating < 0) return "negative";
    return "neutral";
}

export function genderKey(gender) {
    if (gender === "EPalGenderType::Female") return "female";
    if (gender === "EPalGenderType::Male") return "male";
    return null;
}

export function specialTypeKeys(pal = {}) {
    return [
        pal.IsTower && "tower",
        pal.IsBOSS && "boss",
        pal.IsRarePal && "rare",
        pal.IsRAID && "raid",
        pal.IsPREDATOR && "predator",
        pal.IsOilrig && "oilrig",
    ].filter(Boolean);
}

// Alpha and Lucky are the two ends of one switch, so a Pal that has only one of
// the two forms cannot be sent to the other.
export const canToggleBossVariant = pal => Boolean(
    pal?.HasBaseVariant && pal?.HasBossVariant,
);

export function filterPalSkins(skins, selectedPal, hideInvalid = false) {
    const target = selectedPal?.FamilyID
        || selectedPal?.DataAccessKey
        || selectedPal?.CharacterID;
    return (skins ?? []).filter(skin =>
        skin?.TargetPalName === target
        && (!hideInvalid
            || !skin.Invalid
            || skin.SkinName === selectedPal?.SkinName)
    );
}

// Only the work types the Pal can already do: a suitability it has no minimum for
// is one the game never gave it, and raising that is not what "max" means.
export const maximumSuitabilities = (minimums, max) => Object.fromEntries(
    Object.entries(minimums ?? {})
        .filter(([, level]) => level > 0)
        .map(([name]) => [name, max]),
);
