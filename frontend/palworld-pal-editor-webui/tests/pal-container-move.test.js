import assert from "node:assert/strict";
import test from "node:test";

import {
  buildContainerMoveGroups,
  containerMoveDisabledReason,
} from "../src/components/modules/pal-container-move.js";

const container = (id, kind, extra = {}) => ({
  ContainerId: id,
  ContainerKind: kind,
  ContainerLabel: id,
  GroupId: "guild-a",
  Size: 10,
  Occupied: 1,
  MovableInto: true,
  Shared: false,
  ...extra,
});

test("move groups keep bases first, roster-order players next, and other last", () => {
  const players = [
    { InstanceId: "player-b", NickName: "Beta" },
    { InstanceId: "player-a", NickName: "Alpha" },
  ];
  const containers = [
    container("a-special", "special", { OwnerPlayerUId: "player-a" }),
    container("a-storage", "storage", { OwnerPlayerUId: "player-a" }),
    container("base-1", "base"),
    container("shared", "special", { GroupId: null, Shared: true }),
    container("a-party", "party", { OwnerPlayerUId: "player-a" }),
    container("unknown", "unknown", { GroupId: null, MovableInto: false }),
  ];

  const groups = buildContainerMoveGroups(containers, players, "player-a");

  assert.deepEqual(groups.map(group => group.kind), ["bases", "player", "player", "other"]);
  assert.deepEqual(groups.map(group => group.key), ["bases", "player-b", "player-a", "other"]);
  assert.equal(groups[1].selected, false);
  assert.equal(groups[2].selected, true);
  assert.deepEqual(
    groups[2].containers.map(row => row.ContainerKind),
    ["party", "storage", "special"],
  );
  assert.deepEqual(
    groups[3].containers.map(row => row.ContainerId),
    ["shared", "unknown"],
  );
});

test("disabled target reasons are stable and shared cages accept owned Pals", () => {
  const pal = {
    ContainerId: "current",
    OwnerPlayerUId: "player-a",
    group_id: "guild-a",
  };

  assert.equal(containerMoveDisabledReason(container("current", "storage"), pal), "current");
  assert.equal(containerMoveDisabledReason(container("unsafe", "unknown", { MovableInto: false }), pal), "unsafe");
  assert.equal(containerMoveDisabledReason(container("full", "storage", { Occupied: 10 }), pal), "full");
  assert.equal(containerMoveDisabledReason(container("foreign", "storage", { GroupId: "guild-b" }), pal), "different_guild");
  assert.equal(containerMoveDisabledReason(container("shared", "special", { GroupId: null, Shared: true }), pal), null);
  assert.equal(
    containerMoveDisabledReason(
      container("shared", "special", { GroupId: null, Shared: true }),
      { ...pal, OwnerPlayerUId: null },
    ),
    "owner_required",
  );
  assert.equal(
    containerMoveDisabledReason(
      container("dps:player-a", "dps", { StorageKind: "dps", OwnerPlayerUId: "player-a" }),
      { ...pal, StorageKind: "global_palbox" },
    ),
    "gps_player_required",
  );
});
