import assert from "node:assert/strict";
import test from "node:test";

import {
  filterPalPriority,
  groupPalList,
  isCreatedPal,
  isEditedPal,
  matchesPalAttributeFilters,
  matchesPalSessionFilter,
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

test("location sorting groups base-camp Pals by container before slot", () => {
  const baseCampPals = [
    { InstanceId: "container-b-slot-0", ContainerKind: "other", ContainerId: "bbbb", SlotIndex: 0 },
    { InstanceId: "container-a-slot-5", ContainerKind: "other", ContainerId: "aaaa", SlotIndex: 5 },
    { InstanceId: "container-a-slot-1", ContainerKind: "other", ContainerId: "aaaa", SlotIndex: 1 },
  ];

  assert.deepEqual(
    sortPalList(baseCampPals, "location").map(pal => pal.InstanceId),
    ["container-a-slot-1", "container-a-slot-5", "container-b-slot-0"],
  );
});

test("location groups use labels and place all anomalies last", () => {
  const rows = [
    { InstanceId: "bad", ContainerKind: "anomaly", ContainerId: "broken", LocationStatus: "slot_mismatch" },
    { InstanceId: "box", ContainerKind: "storage", ContainerId: "box", ContainerLabel: "Alice · Palbox", SlotIndex: 2, LocationStatus: "ok" },
    { InstanceId: "party", ContainerKind: "party", ContainerId: "party", ContainerLabel: "Alice · Party", SlotIndex: 1, LocationStatus: "ok" },
    { InstanceId: "cage", ContainerKind: "special", ContainerId: "cage", ContainerLabel: "Alice · Viewing cage", SlotIndex: 0, LocationStatus: "ok" },
  ];

  const groups = groupPalList(sortPalList(rows, "location"), "location");

  assert.deepEqual(groups.map(group => group.label), [
    "Alice · Party",
    "Alice · Palbox",
    "Alice · Viewing cage",
    "Location anomaly",
  ]);
  assert.deepEqual(groups.at(-1).pals.map(pal => pal.InstanceId), ["bad"]);
  assert.equal(groupPalList(rows, "paldeck").length, 1);
  assert.equal(groupPalList(rows, "paldeck")[0].label, null);
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

test("Pal attribute filters combine priority and origin tags with union semantics", () => {
  const tagged = [
    { InstanceId: "priority", FavoriteIndex: 2 },
    { InstanceId: "alpha", IsBOSS: true },
    { InstanceId: "lucky", IsRarePal: true },
    { InstanceId: "dna", IsImportedCharacter: true },
    { InstanceId: "human", IsHuman: true },
    { InstanceId: "plain" },
  ];

  assert.deepEqual(tagged.filter(pal => matchesPalAttributeFilters(pal, [])), tagged);
  assert.deepEqual(
    tagged
      .filter(pal => matchesPalAttributeFilters(pal, ["priority-2", "dna", "human"]))
      .map(pal => pal.InstanceId),
    ["priority", "dna", "human"],
  );
  assert.deepEqual(
    tagged
      .filter(pal => matchesPalAttributeFilters(pal, ["alpha", "lucky"]))
      .map(pal => pal.InstanceId),
    ["alpha", "lucky"],
  );
});

test("Editor-created Pals can be filtered explicitly without changing sort order", () => {
  const created = new Set(["storage-2"]);
  assert.deepEqual(pals.filter(pal => isCreatedPal(pal, created)).map(pal => pal.InstanceId), ["storage-2"]);
  assert.equal(isCreatedPal({ InstanceId: "new", IsNewPal: true }, new Set()), true);
});

test("Edited session filtering includes created Pals but created filtering stays specific", () => {
  const edited = new Set(["edited"]);
  const created = new Set(["created"]);
  const unchangedPal = { InstanceId: "unchanged" };
  const editedPal = { InstanceId: "edited" };
  const createdPal = { InstanceId: "created" };

  assert.equal(isEditedPal(editedPal, edited, created), true);
  assert.equal(isEditedPal(createdPal, edited, created), true);
  assert.equal(isEditedPal(unchangedPal, edited, created), false);

  assert.equal(matchesPalSessionFilter(unchangedPal, false, false, edited, created), true);
  assert.equal(matchesPalSessionFilter(editedPal, true, false, edited, created), true);
  assert.equal(matchesPalSessionFilter(createdPal, true, false, edited, created), true);
  assert.equal(matchesPalSessionFilter(editedPal, false, true, edited, created), false);
  assert.equal(matchesPalSessionFilter(createdPal, false, true, edited, created), true);
  assert.equal(matchesPalSessionFilter(editedPal, true, true, edited, created), false);
  assert.equal(matchesPalSessionFilter(createdPal, true, true, edited, created), true);
});
