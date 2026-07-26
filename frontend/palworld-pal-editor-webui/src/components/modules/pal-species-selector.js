const KIND_ORDER = new Map([
    "base",
    "alpha",
    "boss",
    "predator",
    "quest",
    "tower",
    "raid",
    "boss-rush",
    "summon",
    "oilrig",
    "human",
    "other",
].map((kind, index) => [kind, index]));

const normalize = value => String(value ?? "").toLocaleLowerCase();

export function formatPaldeck(value) {
    const text = String(value ?? "");
    const match = text.match(/^(\d+)([A-Za-z]*)$/);
    return match ? `${match[1].padStart(3, "0")}${match[2]}` : text;
}

export const paldeckForRow = row => formatPaldeck(
    row?.Paldeck
    ?? row?.SortingKey
    ?? (row?.PaldeckIndex == null
        ? row?.PaldeckRecordID ?? ""
        : `${row.PaldeckIndex}${row.PaldeckSuffix ?? ""}`),
);

const variantSortKey = row => [
    row?.VariantTags?.includes("base") ? -1 : (KIND_ORDER.get(row?.VariantKind) ?? 99),
    normalize(row?.InternalName),
];

const compareKeys = (left, right) => (
    left[0] - right[0]
    || left[1].localeCompare(right[1], undefined, { numeric: true })
);

export function matchesPalQuery(family, variant, query) {
    const needle = normalize(query).trim();
    if (!needle) return true;
    return [
        family?.Name,
        family?.FamilyID,
        family?.Paldeck,
        variant?.I18n,
        variant?.InternalName,
        variant?.FamilyID,
        variant?.SortingKey,
        variant?.PaldeckRecordID,
        variant?.PaldeckIndex == null
            ? ""
            : `${variant.PaldeckIndex}${variant.PaldeckSuffix ?? ""}`,
    ].some(value => normalize(value).includes(needle));
}

export function hasVisibleVariant(family, id) {
    return Boolean(id && family?.variants.some(variant => variant.InternalName === id));
}

export function moveListboxIndex(current, length, key) {
    if (!length) return -1;
    if (key === "Home") return 0;
    if (key === "End") return length - 1;
    if (key === "ArrowUp") return current < 0 ? length - 1 : (current - 1 + length) % length;
    if (key === "ArrowDown") return current < 0 ? 0 : (current + 1) % length;
    return current;
}

export function buildPalFamilies(rows, currentId, hideInvalid, query) {
    const source = Array.isArray(rows) ? rows : Object.values(rows ?? {});
    const grouped = new Map();
    for (const row of source) {
        if (!row?.InternalName) continue;
        const familyId = row.IsHuman ? row.InternalName : (row.FamilyID || row.InternalName);
        if (!grouped.has(familyId)) grouped.set(familyId, []);
        grouped.get(familyId).push(row);
    }

    const families = [];
    for (const [FamilyID, familyRows] of grouped) {
        const ordered = familyRows.slice().sort((left, right) =>
            compareKeys(variantSortKey(left), variantSortKey(right))
        );
        const representative = ordered.find(row => row.VariantTags?.includes("base"))
            ?? ordered[0];
        const family = {
            FamilyID,
            Name: representative.I18n || FamilyID,
            Paldeck: paldeckForRow(representative),
            IconKey: representative.IconKey || representative.IconAccessKey || "unknown",
            invalidOnly: familyRows.every(row => Boolean(row.Invalid)),
        };
        const visible = ordered.filter(row =>
            !hideInvalid || !row.Invalid || row.InternalName === currentId
        );
        if (!visible.length) continue;

        const familyMatches = [family.Name, family.FamilyID, family.Paldeck]
            .some(value => normalize(value).includes(normalize(query).trim()));
        const matched = familyMatches
            ? visible
            : visible.filter(row => matchesPalQuery(family, row, query));
        if (!matched.length) continue;

        families.push({
            ...family,
            variants: matched.map(row => ({
                ...row,
                current: row.InternalName === currentId,
                warning: Boolean(row.Invalid),
            })),
        });
    }

    return families.sort((left, right) =>
        Number(left.variants.every(row => row.IsHuman))
            - Number(right.variants.every(row => row.IsHuman))
        || Number(!left.Paldeck) - Number(!right.Paldeck)
        || left.Paldeck.localeCompare(right.Paldeck, undefined, { numeric: true })
        || left.Name.localeCompare(right.Name)
        || left.FamilyID.localeCompare(right.FamilyID)
    );
}
