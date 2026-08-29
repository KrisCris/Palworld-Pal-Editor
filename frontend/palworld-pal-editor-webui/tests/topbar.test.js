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
  const savePath = "C:\\Pal\\Saved\\76561198000000000\\8C439FF04713B5F986F9CAB485575089";
  const [{ default: TopBar }, { usePalEditorStore }, { useSessionStore }] = await Promise.all([
    loadVueModule("/src/components/TopBar.vue"),
    loadVueModule("/src/stores/paleditor.js"),
    loadVueModule("/src/stores/session.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  const session = useSessionStore();
  store.I18n = "en";
  // The toolbar follows the app state now: it appears when the editor is what
  // the app is showing, rather than tracking a flag beside it.
  session.appState = "editor";
  session.writeBackPath = savePath;

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
