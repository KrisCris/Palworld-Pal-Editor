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
  { InstanceId: "storage-2", containerKind: "storage", SlotIndex: 2, FavoriteIndex: 1, Paldeck: "002" },
  { InstanceId: "party-4", containerKind: "party", SlotIndex: 4, FavoriteIndex: 2, Paldeck: "004" },
  { InstanceId: "party-0", containerKind: "party", SlotIndex: 0, FavoriteIndex: 3, Paldeck: "003" },
  { InstanceId: "storage-0", containerKind: "storage", SlotIndex: 0, FavoriteIndex: 0, Paldeck: "001" },
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
    { InstanceId: "container-b-slot-0", containerKind: "other", ContainerId: "bbbb", SlotIndex: 0 },
    { InstanceId: "container-a-slot-5", containerKind: "other", ContainerId: "aaaa", SlotIndex: 5 },
    { InstanceId: "container-a-slot-1", containerKind: "other", ContainerId: "aaaa", SlotIndex: 1 },
  ];

  assert.deepEqual(
    sortPalList(baseCampPals, "location").map(pal => pal.InstanceId),
    ["container-a-slot-1", "container-a-slot-5", "container-b-slot-0"],
  );
});

test("location groups use labels and place uncontained Pals last", () => {
  // A Pal whose record occupies no container arrives with neither a container id
  // nor a kind -- there is no anomaly flag to group it by any more.
  const rows = [
    { InstanceId: "bad", containerKind: null, ContainerId: null },
    { InstanceId: "box", containerKind: "storage", ContainerId: "box", containerLabel: "Alice · Palbox", SlotIndex: 2 },
    { InstanceId: "party", containerKind: "party", ContainerId: "party", containerLabel: "Alice · Party", SlotIndex: 1 },
    { InstanceId: "cage", containerKind: "special", ContainerId: "cage", containerLabel: "Alice · Viewing cage", SlotIndex: 0 },
  ];

  const groups = groupPalList(sortPalList(rows, "location"), "location");

  assert.deepEqual(groups.map(group => group.label), [
    "Alice · Party",
    "Alice · Palbox",
    "Alice · Viewing cage",
    "Container unknown",
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

test("created Pals are the ones the backend says it created", () => {
  // There is no frontend set of created keys any more: `changeState` is the
  // backend's own answer, so a Pal created before this browser tab opened still
  // says so.
  assert.equal(isCreatedPal({ recordKey: "new", changeState: "created" }), true);
  assert.equal(isCreatedPal({ recordKey: "old", changeState: "unchanged" }), false);
});

test("Edited session filtering includes created Pals but created filtering stays specific", () => {
  const edited = new Set(["edited"]);
  const unchangedPal = { recordKey: "unchanged" };
  const editedPal = { recordKey: "edited" };
  const createdPal = { recordKey: "created", changeState: "created" };

  assert.equal(isEditedPal(editedPal, edited), true);
  assert.equal(isEditedPal(createdPal, edited), true);
  assert.equal(isEditedPal(unchangedPal, edited), false);

  assert.equal(matchesPalSessionFilter(unchangedPal, false, false, edited), true);
  assert.equal(matchesPalSessionFilter(editedPal, true, false, edited), true);
  assert.equal(matchesPalSessionFilter(createdPal, true, false, edited), true);
  assert.equal(matchesPalSessionFilter(editedPal, false, true, edited), false);
  assert.equal(matchesPalSessionFilter(createdPal, false, true, edited), true);
  assert.equal(matchesPalSessionFilter(editedPal, true, true, edited), false);
  assert.equal(matchesPalSessionFilter(createdPal, true, true, edited), true);
});
