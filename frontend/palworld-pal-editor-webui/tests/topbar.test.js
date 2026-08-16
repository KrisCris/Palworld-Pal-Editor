import assert from "node:assert/strict";
import test, { after } from "node:test";

import { createPinia, setActivePinia } from "pinia";

import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

after(closeVueServer);

test("the loaded-save toolbar prioritizes save actions and keeps cheat options off", async () => {
  const [{ default: TopBar }, { usePalEditorStore }] = await Promise.all([
    loadVueModule("/src/components/TopBar.vue"),
    loadVueModule("/src/stores/paleditor.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  store.I18n = "en";
  store.APP_STATE = "editor";
  store.SAVE_LOADED_FLAG = true;
  store.PAL_WRITE_BACK_PATH = "C:\\Pal\\Saved\\76561198000000000\\8C439FF04713B5F986F9CAB485575089";

  const html = await renderVue(TopBar, { pinia });
  const path = html.match(/<input\b(?=[^>]*class="savePath")([^>]*)>/)?.[1] ?? "";

  assert.match(path, /readonly/);
  assert.doesNotMatch(path, /disabled/);
  assert.match(path, /8C439FF04713B5F986F9CAB485575089/);
  assert.ok(html.indexOf("Reload Save") < html.indexOf("Return to Main Page"));
  assert.ok(html.indexOf("More") < html.indexOf("Donation"));
  const contextBar = html.match(/class="editor-context-bar"[^>]*>([\s\S]*?)<\/div><\/header>/)?.[1] ?? "";
  assert.doesNotMatch(contextBar, /Show Out of Box Pal/);
  assert.doesNotMatch(html, /Show Out of Box Pal/);
  assert.match(html, /aria-pressed="false"[^>]*>[\s\S]*?Show Cheat Options/);
});
