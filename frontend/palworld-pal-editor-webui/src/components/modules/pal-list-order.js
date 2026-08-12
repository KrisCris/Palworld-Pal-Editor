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
  anomaly: 5,
});

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

export const isCreatedPal = (pal, createdIds) => Boolean(
  pal?.IsNewPal || createdIds.has(pal?.InstanceId),
);

export const isEditedPal = (pal, editedIds, createdIds) => Boolean(
  editedIds.has(pal?.InstanceId) || isCreatedPal(pal, createdIds),
);

export const matchesPalSessionFilter = (
  pal,
  editedOnly,
  createdOnly,
  editedIds,
  createdIds,
) => createdOnly
  ? isCreatedPal(pal, createdIds)
  : !editedOnly || isEditedPal(pal, editedIds, createdIds);

export function sortPalList(pals, mode = "paldeck", paldeckFor = pal => pal.Paldeck) {
  return [...pals].sort((left, right) => {
    if (mode === "priority") {
      const priority = Number(right.FavoriteIndex ?? 0) - Number(left.FavoriteIndex ?? 0);
      if (priority) return priority;
    }

    if (mode !== "paldeck") {
      const location = (locationOrder[left.ContainerKind] ?? 2)
        - (locationOrder[right.ContainerKind] ?? 2);
      if (location) return location;
      const missingContainer = Number(!left.ContainerId) - Number(!right.ContainerId);
      if (missingContainer) return missingContainer;
      const container = textOrder(left.ContainerId, right.ContainerId);
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
    const anomalous = pal.LocationStatus && pal.LocationStatus !== "ok";
    const key = anomalous ? "anomaly" : pal.ContainerId || "unknown";
    let group = groups.at(-1);
    if (!group || group.key !== key) {
      group = {
        key,
        label: anomalous
          ? "Location anomaly"
          : pal.ContainerLabel || `Container ${pal.ContainerId || "unknown"}`,
        pals: [],
      };
      groups.push(group);
    }
    group.pals.push(pal);
  }
  return groups;
}
