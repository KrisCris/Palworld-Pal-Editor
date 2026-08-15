const playerContainerOrder = Object.freeze({ party: 0, storage: 1, special: 2 });

export function buildContainerMoveGroups(containers, players, selectedPlayerId) {
  const rows = [...(containers ?? [])];
  const groups = [];
  const globalContainers = rows.filter(container => container.StorageKind === "global_palbox");
  if (globalContainers.length) groups.push({
    key: "global_palbox",
    kind: "global_palbox",
    selected: false,
    label: globalContainers[0].ContainerLabel,
    containers: globalContainers,
  });
  groups.push({
    key: "bases",
    kind: "bases",
    selected: false,
    containers: rows.filter(container => container.ContainerKind === "base"),
  });

  for (const player of players ?? []) {
    groups.push({
      key: player.InstanceId,
      kind: "player",
      label: player.NickName,
      selected: player.InstanceId === selectedPlayerId,
      containers: rows
        .filter(container => container.OwnerPlayerUId === player.InstanceId)
        .sort((left, right) => (
          (playerContainerOrder[left.ContainerKind] ?? 99)
          - (playerContainerOrder[right.ContainerKind] ?? 99)
        )),
    });
  }

  groups.push({
    key: "other",
    kind: "other",
    selected: false,
    containers: rows.filter(container => (
      container.ContainerKind !== "base"
      && container.StorageKind !== "global_palbox"
      && !container.OwnerPlayerUId
    )),
  });
  return groups;
}

export function containerMoveDisabledReason(container, pal) {
  if ((container.StorageKey && container.StorageKey === pal.StorageKey)
    || (!container.StorageKey && container.ContainerId === pal.ActualContainerId)) return "current";
  if (pal.StorageKind === "global_palbox") {
    const ownedPlayerContainer = container.StorageKind === "world"
      && ["party", "storage"].includes(container.ContainerKind)
      && container.OwnerPlayerUId;
    if (!ownedPlayerContainer) return "gps_player_required";
    return container.Occupied >= container.Size ? "full" : null;
  }
  if (container.StorageKind === "global_palbox") {
    if (!container.CloneableInto) return "unsafe";
    return container.Occupied >= container.Size ? "full" : null;
  }
  if (!container.MovableInto) return "unsafe";
  if (container.Occupied >= container.Size) return "full";
  if (container.Shared) return pal.OwnerPlayerUId ? null : "owner_required";
  if (container.GroupId !== pal.group_id) return "different_guild";
  return null;
}
