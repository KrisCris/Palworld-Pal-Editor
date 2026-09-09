import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { createPinia, setActivePinia } from "pinia";

import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

after(closeVueServer);

const dialogPath = new URL("../src/components/PalContainerMoveDialog.vue", import.meta.url);
const editorPath = new URL("../src/components/PalEditor.vue", import.meta.url);

test("Pal movement uses a glass two-pane confirmation dialog", async () => {
  const source = await readFile(dialogPath, "utf8");

  assert.match(source, /editor-modal-overlay/);
  assert.match(source, /editor-glass-surface/);
  assert.match(source, /role="dialog"/);
  assert.match(source, /move-dialog__groups/);
  assert.match(source, /move-dialog__containers/);
  assert.match(source, /formatStorageLabel/);
  assert.doesNotMatch(source, /\{\{\s*storage\.label\s*\}\}/);
  assert.match(source, /aria-disabled/);
  assert.match(source, /Editor_Move_Pal/);
  // Whether a target is offered and why not is the backend's answer for this
  // source-and-target pair, not a rule the dialog re-derives from the kind.
  assert.match(source, /moveReasonKey/);
  assert.match(source, /storagesStore\.capability/);
  assert.doesNotMatch(source, /MovableInto|ContainerKind/);
});

test("Pal update comparison is a centered directional glass layer", async () => {
  const [{ default: PalContainerMoveDialog }, { useStoragesStore }] = await Promise.all([
    loadVueModule("/src/components/PalContainerMoveDialog.vue"),
    loadVueModule("/src/stores/storages.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const storages = useStoragesStore();
  const pal = {
    CharacterID: "JetDragon",
    DisplayName: "Jetragon",
    IconKey: "JetDragon",
    Level: 62,
    Rank: 1,
    FriendshipLevel: 0,
    FavoriteIndex: 2,
    IsBOSS: true,
    IsAwakening: true,
    IsImportedCharacter: true,
  };
  storages.conflict = {
    incoming: pal,
    existing: { ...pal, Level: 71 },
    fieldChanges: { Level: { Incoming: 62, Existing: 71 } },
    candidates: [{
      recordKey: "world:pal-1",
      storageKey: "world-container:1",
      SlotIndex: 3,
      label: "Player · Palbox",
    }],
    sourceRecordKey: "world:pal-2",
    targetStorageKey: "global-palbox",
  };

  const html = await renderVue(PalContainerMoveDialog, { pinia });

  assert.match(html, /<\/section><div class="move-dialog__preview"/);
  assert.match(html, /move-dialog__comparison-arrow/);
  assert.match(html, /pal-brief--incoming/);
  assert.match(html, /pal-brief--existing/);
  assert.equal((html.match(/pal-brief__friendship-row/g) || []).length, 2);
  assert.match(html, /game-priority-icon/);
  assert.match(html, /game-dna-icon/);
  assert.match(html, /image\/ui\/boss/);
});

test("PalEditor opens the dialog instead of embedding movement SearchSelect controls", async () => {
  const source = await readFile(editorPath, "utf8");

  assert.match(source, /PalContainerMoveDialog/);
  assert.doesNotMatch(source, /moveTargetOptions/);
  assert.doesNotMatch(source, /pal-move-control/);
});

test("every locale defines the movement dialog and disabled-reason labels", async () => {
  const localeDirectory = new URL("../src/i18n/", import.meta.url);
  const files = (await readdir(localeDirectory)).filter(
    file => file.endsWith(".js") && file !== "index.js",
  );
  const keys = [
    "Editor_Move_Dialog_Title",
    "Editor_Move_Dialog_Subtitle",
    "Editor_Move_Groups",
    "Editor_Move_Containers",
    "Editor_Move_Group_Bases",
    "Editor_Move_Group_Other",
    "Editor_Move_Current_Player",
    "Editor_Move_No_Containers",
    "Editor_Move_Reason_Current",
    "Editor_Move_Reason_Full",
    "Editor_Move_Reason_Duplicate",
    "Editor_Move_Reason_Unsafe",
    "Editor_Move_Reason_DifferentGuild",
    "Editor_Move_Reason_OwnerRequired",
    "Editor_Move_Reason_GpsPlayerRequired",
    "Editor_Container_Base",
    "Editor_Container_Party",
    "Editor_Container_Palbox",
    "Editor_Container_ViewingCage",
    "Editor_Container_Special",
    "Editor_Container_Unknown",
    "Editor_Container_Anomaly",
  ];

  for (const file of files) {
    const source = await readFile(new URL(file, localeDirectory), "utf8");
    for (const key of keys) assert.ok(source.includes(`${key}:`), `${file}: ${key}`);
  }
});
