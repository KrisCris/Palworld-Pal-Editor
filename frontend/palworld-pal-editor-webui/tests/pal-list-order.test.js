import assert from "node:assert/strict";
import test from "node:test";

import {
  filterPalPriority,
  isCreatedPal,
  sortPalList,
} from "../src/components/modules/pal-list-order.js";

const pals = [
  { InstanceId: "storage-2", ContainerKind: "storage", SlotIndex: 2, FavoriteIndex: 1, Paldeck: "002" },
  { InstanceId: "party-4", ContainerKind: "party", SlotIndex: 4, FavoriteIndex: 2, Paldeck: "004" },
  { InstanceId: "party-0", ContainerKind: "party", SlotIndex: 0, FavoriteIndex: 3, Paldeck: "003" },
  { InstanceId: "storage-0", ContainerKind: "storage", SlotIndex: 0, FavoriteIndex: 0, Paldeck: "001" },
];

test("Pal list sorting follows the explicitly selected mode", () => {
  assert.deepEqual(
    sortPalList(pals, "location").map(pal => pal.InstanceId),
    ["party-0", "party-4", "storage-0", "storage-2"],
  );
  assert.deepEqual(
    sortPalList([...pals].reverse(), "priority").map(pal => pal.InstanceId),
    ["party-0", "party-4", "storage-2", "storage-0"],
  );
  assert.deepEqual(
    sortPalList([...pals].reverse(), "paldeck").map(pal => pal.InstanceId),
    ["storage-0", "storage-2", "party-0", "party-4"],
  );
});

test("Paldeck sorting places Pals without a Paldeck number last", () => {
  const withoutPaldeck = { InstanceId: "human", Paldeck: "" };

  assert.deepEqual(
    sortPalList([withoutPaldeck, ...pals], "paldeck").map(pal => pal.InstanceId),
    ["storage-0", "storage-2", "party-0", "party-4", "human"],
  );
});

test("Pal priority filtering recognizes unprioritized and I to III", () => {
  assert.deepEqual(pals.filter(pal => filterPalPriority(pal, "all")), pals);
  assert.deepEqual(pals.filter(pal => filterPalPriority(pal, "0")).map(pal => pal.InstanceId), ["storage-0"]);
  assert.deepEqual(pals.filter(pal => filterPalPriority(pal, "1")).map(pal => pal.InstanceId), ["storage-2"]);
  assert.deepEqual(pals.filter(pal => filterPalPriority(pal, "2")).map(pal => pal.InstanceId), ["party-4"]);
  assert.deepEqual(pals.filter(pal => filterPalPriority(pal, "3")).map(pal => pal.InstanceId), ["party-0"]);
});

test("Editor-created Pals can be filtered explicitly without changing sort order", () => {
  const created = new Set(["storage-2"]);
  assert.deepEqual(pals.filter(pal => isCreatedPal(pal, created)).map(pal => pal.InstanceId), ["storage-2"]);
  assert.equal(isCreatedPal({ InstanceId: "new", IsNewPal: true }, new Set()), true);
});
