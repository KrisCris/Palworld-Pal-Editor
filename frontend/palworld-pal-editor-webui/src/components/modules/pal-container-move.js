const playerContainerOrder = Object.freeze({ party: 0, storage: 1, special: 2 });

export function buildContainerMoveGroups(containers, players, selectedPlayerId) {
  const rows = [...(containers ?? [])];
  const groups = [{
    key: "bases",
    kind: "bases",
    selected: false,
    containers: rows.filter(container => container.ContainerKind === "base"),
  }];

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
      container.ContainerKind !== "base" && !container.OwnerPlayerUId
    )),
  });
  return groups;
}

export function containerMoveDisabledReason(container, pal) {
  if (container.ContainerId === pal.ActualContainerId) return "current";
  if (!container.MovableInto) return "unsafe";
  if (container.Occupied >= container.Size) return "full";
  if (container.Shared) return pal.OwnerPlayerUId ? null : "owner_required";
  if (container.GroupId !== pal.group_id) return "different_guild";
  return null;
}
