import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { createPinia, setActivePinia } from "pinia";

import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import ja from "../src/i18n/ja.js";
import zhCN from "../src/i18n/zh-CN.js";
import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

after(closeVueServer);

const pals = [
  { InstanceId: "ordinary", DisplayName: "Ordinary Pal", changeState: "created" },
  { InstanceId: "alpha", DisplayName: "Alpha Pal", IsBOSS: true },
  { InstanceId: "lucky", DisplayName: "Lucky Pal", IsRarePal: true },
  { InstanceId: "both", DisplayName: "Alpha Lucky Pal", IsBOSS: true, IsRarePal: true },
].map(pal => ({
  recordKey: `world:${pal.InstanceId}`,
  CharacterID: "TestPal",
  DataAccessKey: "TestPal",
  Paldeck: "001",
  Gender: "NONE",
  IconAccessKey: "TestPal",
  containerKind: "storage",
  isAway: false,
  changeState: "unchanged",
  ...pal,
}));

function row(html, value) {
  const match = html.match(new RegExp(`<button\\b(?=[^>]*\\bvalue="${value}")[^>]*>([\\s\\S]*?)<\\/button>`));
  assert.ok(match, `${value} row is rendered`);
  return match[1];
}

// The roster the list renders: keys in `stores/rosters`, Pals in `stores/pals`.
async function showRoster(rows = pals, { edited = [] } = {}) {
  const [{ default: PalList }, { usePalEditorStore }, { usePalsStore }, { useRostersStore }, { useCatalogsStore }] =
    await Promise.all([
      loadVueModule("/src/components/PalList.vue"),
      loadVueModule("/src/stores/paleditor.js"),
      loadVueModule("/src/stores/pals.js"),
      loadVueModule("/src/stores/rosters.js"),
      loadVueModule("/src/stores/catalogs.js"),
    ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  const palsStore = usePalsStore();
  const rostersStore = useRostersStore();
  useCatalogsStore().pals = [{ InternalName: "TestPal", Paldeck: 1 }];
  palsStore.upsertSummaries(rows);
  for (const recordKey of edited) palsStore.markEdited(recordKey);
  rostersStore.recordKeysByRoster.set("player:player-1", rows.map(row => row.recordKey));
  rostersStore.activeRosterKey = "player:player-1";
  return { pinia, store, palsStore, rostersStore, PalList };
}

test("Pal rows render translated accessible status text for every Alpha and Lucky combination", async () => {
  const { pinia, PalList } = await showRoster();

  const html = await renderVue(PalList, { pinia });
  for (const [value, status] of [
    ["world:ordinary", "Status: Ordinary"],
    ["world:alpha", "Status: Alpha"],
    ["world:lucky", "Status: Lucky"],
    ["world:both", "Status: Alpha and Lucky"],
  ]) {
    const content = row(html, value);
    assert.match(content, new RegExp(`<span class="sr-only"[^>]*>${status}<\\/span>`));
    assert.doesNotMatch(content, /<(?:img|span class="pal-portrait__marker")[^>]*(?:alt="[^"]+"|aria-hidden="false")/);
  }
  assert.match(row(html, "world:ordinary"), /class="new-pal-marker"/);
  assert.match(row(html, "world:ordinary"), /New, unsaved Pal/);
  assert.doesNotMatch(row(html, "world:alpha"), /class="new-pal-marker"|New, unsaved Pal/);
});

test("session filters use pressed buttons and edited-only Pals get a distinct marker", async () => {
  const { pinia, PalList } = await showRoster(pals, { edited: ["world:alpha"] });

  const html = await renderVue(PalList, { pinia });

  assert.match(html, /<button[^>]*class="pal-list-menu__session-button"[^>]*aria-pressed="false"[^>]*>[^]*Edited this session/);
  assert.match(html, /<button[^>]*class="pal-list-menu__session-button"[^>]*aria-pressed="false"[^>]*>[^]*Created this session/);
  assert.match(row(html, "world:alpha"), /class="edited-pal-marker"/);
  assert.match(row(html, "world:alpha"), /Edited this session/);
  assert.doesNotMatch(row(html, "world:ordinary"), /class="edited-pal-marker"/);
  assert.match(row(html, "world:ordinary"), /class="new-pal-marker"/);
});

test("Pal row status phrases are translated in all UI locales", () => {
  const expected = [
    [en, ["Status: Ordinary", "Status: Alpha", "Status: Lucky", "Status: Alpha and Lucky"]],
    [fr, ["Statut : Ordinaire", "Statut : Alpha", "Statut : Chanceux", "Statut : Alpha et Chanceux"]],
    [ja, ["状態：通常", "状態：ボス", "状態：希少", "状態：ボス・希少"]],
    [zhCN, ["状态：普通", "状态：头目", "状态：稀有", "状态：头目且稀有"]],
  ];
  const keys = ["Ordinary", "Alpha", "Lucky", "AlphaLucky"];
  for (const [locale, values] of expected) {
    keys.forEach((key, index) => assert.equal(locale[`PalList_Status_${key}`], values[index]));
  }

  assert.equal(en.PalList_Status_Unsaved, "New, unsaved Pal");
  assert.equal(fr.PalList_Status_Unsaved, "Nouveau Pal non enregistré");
  assert.equal(ja.PalList_Status_Unsaved, "未保存の新しいパル");
  assert.equal(zhCN.PalList_Status_Unsaved, "未保存的新帕鲁");
});

test("Pal reselection scrolls only as far as needed inside the roster", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /scrollIntoView\(\{ behavior: 'smooth', block: 'nearest' \}\)/);
  assert.doesNotMatch(source, /isElementInViewport/);
});

test("Pal sort and filter controls dismiss outside and escape adjacent rails", async () => {
  const [source, workspace] = await Promise.all([
    readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8"),
    readFile(new URL("../src/views/EditorView.vue", import.meta.url), "utf8"),
  ]);
  assert.match(source, /import \{ closeDisclosureOnOutsidePointer \} from/);
  assert.match(source, /ref="sortMenu"/);
  assert.match(source, /window\.addEventListener\('pointerdown', closeSortMenuOnOutsidePointer\)/);
  assert.match(source, /window\.removeEventListener\('pointerdown', closeSortMenuOnOutsidePointer\)/);
  assert.match(source, /\.pal-list-menu__popover\s*\{[^}]*left:\s*0;/s);
  assert.match(workspace, /\.editor-roster--players\s*\{[^}]*z-index:\s*1;/s);
  assert.match(workspace, /\.editor-roster--pals\s*\{[^}]*z-index:\s*2;[^}]*overflow:\s*visible;/s);
});

test("selected Pal rows use one gender-aware accent for the full selection treatment", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /\.pal-row\s*\{[^}]*--pal-row-accent:\s*var\(--editor-color-focus\)/s);
  assert.match(source, /\.pal-row\.male\s*\{[^}]*--pal-row-accent:\s*var\(--editor-color-male\)/s);
  assert.match(source, /\.pal-row\.female\s*\{[^}]*--pal-row-accent:\s*var\(--editor-color-female\)/s);
  assert.match(source, /\.pal-row\[aria-current="true"\]\s*\{[^}]*border-color:\s*var\(--pal-row-accent\)[^}]*box-shadow:[^}]*var\(--pal-row-accent\)/s);
});

test("Pal portraits expose the in-game priority icon", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /image\/ui\/priority-/);
  assert.match(source, /pal\.FavoriteIndex > 0/);
});

test("collapsed Pal roster preview retains sort, filter, and add actions", async () => {
  const { pinia, PalList } = await showRoster();

  const html = await renderVue(PalList, { pinia, props: { preview: true } });
  assert.match(html, /pal-roster--preview/);
  assert.match(html, /class="pal-list-menu"/);
  assert.match(html, /aria-label="Sort and filter Pals"/);
  assert.match(html, /name="add_pal"/);

  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /\.pal-roster--preview\s+\.pal-list-menu__popover\s*\{[^}]*right:\s*0[^}]*left:\s*auto[^}]*width:\s*min\(13rem,/s);
});

test("every Pal stays visible and DPS metadata is marked as away from nearby containers", async () => {
  // `isAway` is the backend's answer now; the list no longer re-derives it from
  // a container kind and an ownership flag.
  const awayPal = {
    ...pals[0],
    InstanceId: "away-world",
    recordKey: "world:away-world",
    DisplayName: "Away World Pal",
    isAway: true,
  };
  const dpsPal = {
    ...pals[1],
    InstanceId: "dps-pal",
    recordKey: "dps:player:dps-pal",
    DisplayName: "DPS Pal",
    storageKind: "dps",
    containerKind: "dps",
    isAway: true,
  };
  const { pinia, PalList } = await showRoster([awayPal, dpsPal]);

  const html = await renderVue(PalList, { pinia });

  assert.match(row(html, "world:away-world"), /Away World Pal/);
  assert.match(html, /<button[^>]*class="[^"]*out-of-container[^"]*"[^>]*value="dps:player:dps-pal"/);
});

test("Global Palbox roster label follows frontend locale without backend translation data", async () => {
  const [{ default: PlayerList }, { useAppStore }, { useRostersStore }] = await Promise.all([
    loadVueModule("/src/components/PlayerList.vue"),
    loadVueModule("/src/stores/app.js"),
    loadVueModule("/src/stores/rosters.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  useAppStore().locale = "zh-CN";
  useRostersStore().rosters = [{
    rosterKey: "global-palbox",
    kind: "global_palbox",
    label: "stale backend label",
    playerUid: null,
  }];

  const html = await renderVue(PlayerList, { pinia });

  assert.match(html, />跨界帕鲁终端</);
  assert.doesNotMatch(html, /stale backend label/);
});

test("Pal list exposes game-derived DNA origin markers and union filter buttons", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /pal\.IsImportedCharacter/);
  assert.match(source, /image\/ui\/dna/);
  assert.match(source, /rostersStore\.attributeFilters/);
  assert.match(source, /matchesPalAttributeFilters/);
  for (const key of ["priority-1", "priority-2", "priority-3", "alpha", "lucky", "dna", "human"]) {
    assert.match(source, new RegExp(`key: '${key}'`));
  }
});

test("location sorting renders container headers and explicit safety markers", async () => {
  const [listSource, editorSource, moveDialogSource] = await Promise.all([
    readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8"),
    readFile(new URL("../src/components/PalEditor.vue", import.meta.url), "utf8"),
    readFile(new URL("../src/components/PalContainerMoveDialog.vue", import.meta.url), "utf8"),
  ]);
  assert.match(listSource, /visiblePalGroups/);
  assert.match(listSource, /class="container-heading"/);
  assert.match(listSource, /formatContainerLabel/);
  assert.match(listSource, /containerLabel\(group\)/);
  assert.match(listSource, /group\.container\.Occupied.*group\.container\.Size/s);
  assert.match(listSource, /pal\.IsExpeditionPal/);
  assert.doesNotMatch(listSource, /v-if="[^"]*BASE_ROSTER_KEY"[^>]*name="add_pal"/);

  assert.match(editorSource, /PalContainerMoveDialog/);
  assert.match(moveDialogSource, /palStore\.movePal\(pendingContainerId\.value\)/);
  assert.match(editorSource, /IsExpeditionPal[\s\S]*!pal\.storageKey/);
});
