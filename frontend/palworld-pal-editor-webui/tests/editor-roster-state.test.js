import assert from "node:assert/strict";
import test, { after, afterEach } from "node:test";

import { closeVueServer, loadVueModule } from "./vue-render.js";

after(closeVueServer);

const originalStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
afterEach(() => {
  delete globalThis.localStorage;
  if (originalStorage) Object.defineProperty(globalThis, "localStorage", originalStorage);
});

function setStorage(value) {
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value });
}

test("roster collapse state reads and persists each key independently", async () => {
  const { readRosterCollapsed, persistRosterCollapsed } = await loadVueModule("/src/views/EditorView.vue");
  assert.equal(typeof readRosterCollapsed, "function");
  assert.equal(typeof persistRosterCollapsed, "function");

  const values = new Map([["editor.playersCollapsed", "true"]]);
  const storage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
  setStorage(storage);

  assert.equal(readRosterCollapsed("editor.playersCollapsed"), true);
  assert.equal(readRosterCollapsed("editor.palsCollapsed"), false);
  persistRosterCollapsed("editor.playersCollapsed", false);
  persistRosterCollapsed("editor.palsCollapsed", true);
  assert.deepEqual(Object.fromEntries(values), {
    "editor.playersCollapsed": "false",
    "editor.palsCollapsed": "true",
  });
});

test("missing global storage falls back through the production call boundary", async () => {
  const { readRosterCollapsed, persistRosterCollapsed } = await loadVueModule("/src/views/EditorView.vue");
  assert.equal(typeof readRosterCollapsed, "function");
  assert.equal(typeof persistRosterCollapsed, "function");
  delete globalThis.localStorage;

  assert.equal(readRosterCollapsed("editor.playersCollapsed"), false);
  assert.doesNotThrow(() => persistRosterCollapsed("editor.playersCollapsed", true));
});

test("a throwing global storage getter is resolved inside the helper guard", async () => {
  const { readRosterCollapsed, persistRosterCollapsed } = await loadVueModule("/src/views/EditorView.vue");
  let accesses = 0;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get() {
      accesses += 1;
      throw new Error("blocked");
    },
  });

  assert.equal(readRosterCollapsed("editor.playersCollapsed"), false);
  assert.doesNotThrow(() => persistRosterCollapsed("editor.playersCollapsed", true));
  assert.equal(accesses, 2);
});
