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
  { InstanceId: "ordinary", DisplayName: "Ordinary Pal" },
  { InstanceId: "alpha", DisplayName: "Alpha Pal", IsBOSS: true },
  { InstanceId: "lucky", DisplayName: "Lucky Pal", IsRarePal: true },
  { InstanceId: "both", DisplayName: "Alpha Lucky Pal", IsBOSS: true, IsRarePal: true },
].map(pal => ({
  CharacterID: "TestPal",
  DataAccessKeyOG: "TestPal",
  Gender: "NONE",
  IconAccessKey: "TestPal",
  in_owner_palbox: true,
  ...pal,
}));

function row(html, value) {
  const match = html.match(new RegExp(`<button\\b(?=[^>]*\\bvalue="${value}")[^>]*>([\\s\\S]*?)<\\/button>`));
  assert.ok(match, `${value} row is rendered`);
  return match[1];
}

test("Pal rows render translated accessible status text for every Alpha and Lucky combination", async () => {
  const [{ default: PalList }, { usePalEditorStore }] = await Promise.all([
    loadVueModule("/src/components/PalList.vue"),
    loadVueModule("/src/stores/paleditor.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  store.PAL_MAP = new Map(pals.map(pal => [pal.InstanceId, pal]));
  store.PAL_STATIC_DATA = { TestPal: { Paldeck: 1 } };

  const html = await renderVue(PalList, { pinia });
  for (const [value, status] of [
    ["ordinary", "Status: Ordinary"],
    ["alpha", "Status: Alpha"],
    ["lucky", "Status: Lucky"],
    ["both", "Status: Alpha and Lucky"],
  ]) {
    const content = row(html, value);
    assert.match(content, new RegExp(`<span class="sr-only"[^>]*>${status}<\\/span>`));
    assert.doesNotMatch(content, /<(?:img|span class="pal-portrait__marker")[^>]*(?:alt="[^"]+"|aria-hidden="false")/);
  }
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
});

test("Pal reselection scrolls only as far as needed inside the roster", async () => {
  const source = await readFile(new URL("../src/components/PalList.vue", import.meta.url), "utf8");
  assert.match(source, /scrollIntoView\(\{ behavior: 'smooth', block: 'nearest' \}\)/);
  assert.doesNotMatch(source, /isElementInViewport/);
});
