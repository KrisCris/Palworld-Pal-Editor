const textOrder = (left, right) => String(left ?? "").localeCompare(
  String(right ?? ""), undefined, { numeric: true, sensitivity: "base" },
);

const locationOrder = Object.freeze({
  party: 0,
  storage: 1,
  special: 2,
  other: 2,
  base: 3,
  unknown: 4,
});

// A Pal whose record occupies no container has no containerKind at all; it sorts
// with the unknown containers, at the end.
const kindOrder = kind => locationOrder[kind] ?? locationOrder.unknown;

export const filterPalPriority = (pal, priority) => (
  priority === "all" || Number(pal?.FavoriteIndex ?? 0) === Number(priority)
);

const palAttributeFilterMatches = Object.freeze({
  "priority-1": pal => Number(pal?.FavoriteIndex ?? 0) === 1,
  "priority-2": pal => Number(pal?.FavoriteIndex ?? 0) === 2,
  "priority-3": pal => Number(pal?.FavoriteIndex ?? 0) === 3,
  alpha: pal => Boolean(pal?.IsBOSS),
  lucky: pal => Boolean(pal?.IsRarePal),
  dna: pal => Boolean(pal?.IsImportedCharacter),
  human: pal => Boolean(pal?.IsHuman),
});

export const matchesPalAttributeFilters = (pal, filters) => (
  !filters?.length || filters.some(filter => palAttributeFilterMatches[filter]?.(pal))
);

// `changeState` is the backend's own answer and the only authority for both of
// these: anything it does not call `unchanged` has been touched this session.
export const isCreatedPal = pal => pal?.changeState === "created";

export const isEditedPal = pal => Boolean(
  pal?.changeState && pal.changeState !== "unchanged",
);

export const matchesPalSessionFilter = (pal, editedOnly, createdOnly) => (
  createdOnly ? isCreatedPal(pal) : !editedOnly || isEditedPal(pal)
);

export function sortPalList(pals, mode = "paldeck", paldeckFor = pal => pal.Paldeck) {
  return [...pals].sort((left, right) => {
    if (mode === "priority") {
      const priority = Number(right.FavoriteIndex ?? 0) - Number(left.FavoriteIndex ?? 0);
      if (priority) return priority;
    }

    if (mode !== "paldeck") {
      const location = kindOrder(left.containerKind) - kindOrder(right.containerKind);
      if (location) return location;
      const leftStorageKey = left.storageKey || left.ContainerId;
      const rightStorageKey = right.storageKey || right.ContainerId;
      const missingContainer = Number(!leftStorageKey) - Number(!rightStorageKey);
      if (missingContainer) return missingContainer;
      const container = textOrder(leftStorageKey, rightStorageKey);
      if (container) return container;
      const slot = (left.SlotIndex ?? Number.MAX_SAFE_INTEGER)
        - (right.SlotIndex ?? Number.MAX_SAFE_INTEGER);
      if (slot) return slot;
    } else {
      const leftPaldeck = paldeckFor(left);
      const rightPaldeck = paldeckFor(right);
      const missing = Number(!leftPaldeck) - Number(!rightPaldeck);
      if (missing) return missing;
      const paldeck = textOrder(leftPaldeck, rightPaldeck);
      if (paldeck) return paldeck;
    }

    return textOrder(left.InstanceId, right.InstanceId);
  });
}

export function groupPalList(pals, mode = "paldeck") {
  if (mode !== "location") {
    return [{ key: "all", label: null, pals: [...pals] }];
  }

  const groups = [];
  for (const pal of pals) {
    const storageKey = pal.storageKey || pal.ContainerId;
    const key = storageKey || "unknown";
    let group = groups.at(-1);
    if (!group || group.key !== key) {
      group = {
        key,
        label: pal.containerLabel || `Container ${storageKey || "unknown"}`,
        pals: [],
      };
      groups.push(group);
    }
    group.pals.push(pal);
  }
  return groups;
}
