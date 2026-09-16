import assert from "node:assert/strict";
import test from "node:test";

import {
  MOVE_REASON_FALLBACK_KEY,
  buildStorageMoveGroups,
  moveReasonKey,
} from "../src/components/pal-storage-move.js";
import en from "../src/i18n/en.js";

const storage = (storageKey, group, order, groupOrder) => ({
  storageKey,
  navigationGroupKey: group,
  navigationGroupLabel: group === "player:alice" ? "Alice" : null,
  navigationGroupOrder: groupOrder,
  order,
});

test("move groups follow the backend's grouping and both of its orderings", () => {
  const groups = buildStorageMoveGroups(
    [
      storage("world-container:party-b", "player:bob", 0, 2),
      storage("world-container:palbox-a", "player:alice", 1, 1),
      storage("global-palbox", "other", 0, 3),
      storage("world-container:base-1", "bases", 0, 0),
      storage("world-container:party-a", "player:alice", 0, 1),
    ],
    "player:alice",
  );

  assert.deepEqual(groups.map(group => group.key), ["bases", "player:alice", "player:bob", "other"]);
  assert.deepEqual(groups.map(group => group.selected), [false, true, false, false]);
  assert.deepEqual(
    groups[1].storages.map(row => row.storageKey),
    ["world-container:party-a", "world-container:palbox-a"],
  );
  // The heading is the backend's where it is data, and null where the frontend
  // holds the translated word for it.
  assert.equal(groups[1].label, "Alice");
  assert.equal(groups[0].label, null);
});

test("every refusal the backend can send reaches a message the locales have", () => {
  const reasons = [
    "ALREADY_IN_TARGET",
    "TARGET_FULL",
    "DUPLICATE_IN_TARGET",
    "CROSS_GUILD_UNSUPPORTED",
    "OWNER_REQUIRED",
    "GPS_PLAYER_TARGET_REQUIRED",
    "TARGET_NOT_MOVABLE",
    "SOURCE_LOCATION_ANOMALY",
  ];
  for (const reason of reasons) {
    assert.ok(en[moveReasonKey(reason)], `${reason} has no message`);
  }

  // A target that simply cannot take a Pal right now shares one message, and so
  // does a code this build has never heard of -- never a blank row.
  assert.equal(moveReasonKey("TARGET_NOT_MOVABLE"), MOVE_REASON_FALLBACK_KEY);
  assert.equal(moveReasonKey("SOMETHING_NEWER_THAN_THIS_BUILD"), MOVE_REASON_FALLBACK_KEY);
  // An allowed target has no reason and shows no message.
  assert.equal(moveReasonKey(null), null);
});
