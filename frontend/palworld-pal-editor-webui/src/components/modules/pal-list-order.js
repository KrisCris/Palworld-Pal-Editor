const textOrder = (left, right) => String(left ?? "").localeCompare(
  String(right ?? ""), undefined, { numeric: true, sensitivity: "base" },
);

const locationOrder = Object.freeze({ party: 0, storage: 1, other: 2 });

export const filterPalPriority = (pal, priority) => (
  priority === "all" || Number(pal?.FavoriteIndex ?? 0) === Number(priority)
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
