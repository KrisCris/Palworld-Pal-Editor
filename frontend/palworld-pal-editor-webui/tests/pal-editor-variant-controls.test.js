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

function button(html, name) {
  const match = html.match(new RegExp(`<button\\b(?=[^>]*\\bname="${name}")([^>]*)>([\\s\\S]*?)<\\/button>`));
  assert.ok(match, `${name} control is rendered`);
  return { attributes: match[1], content: match[2] };
}

async function renderPalEditorFixture() {
  const [{ default: PalEditor }, { usePalEditorStore }] = await Promise.all([
    loadVueModule("/src/components/PalEditor.vue"),
    loadVueModule("/src/stores/paleditor.js"),
  ]);
  const pinia = createPinia();
  setActivePinia(pinia);
  const store = usePalEditorStore();
  store.PAL_STATIC_DATA = { TestPal: { I18n: "Test Pal", Elements: [], Paldeck: 1 } };
  store.SELECTED_PAL_DATA = {
    DataAccessKey: "TestPal",
    DataAccessKeyOG: "TestPal",
    EquipWaza: [],
    FriendshipLevel: 0,
    HasBaseVariant: true,
    HasBossVariant: true,
    IconAccessKey: "TestPal",
    InternalName: "TestPal",
    IsBOSS: true,
    IsHuman: false,
    IsRarePal: true,
    Level: 1,
    MasteredWaza: [],
    PassiveSkillList: [],
    Suitabilities: {},
    SuitabilityMinimums: {},
    isEquipSkillFull: () => false,
    isEquippedPassiveSkill: () => false,
    isEquippedSkill: () => false,
    isMasteredSkill: () => false,
  };

  return renderVue(PalEditor, { pinia });
}

test("variant controls expose Alpha and Lucky actions with their game markers", async () => {
  const html = await renderPalEditorFixture();
  const alpha = button(html, "IsBOSS");
  const lucky = button(html, "IsRarePal");

  assert.match(alpha.attributes, /class="[^"]*editor-button--secondary[^"]*is-active/);
  assert.match(alpha.attributes, /aria-pressed="true"/);
  assert.match(alpha.attributes, /aria-label="Toggle Alpha status"/);
  assert.match(alpha.content, /<img\b[^>]*src="\/image\/ui\/boss"[^>]*alt=""/);
  assert.doesNotMatch(alpha.content, /#crown/);
  assert.match(lucky.attributes, /aria-label="Toggle Lucky status"/);
  assert.match(lucky.attributes, /class="[^"]*editor-button--secondary[^"]*is-active/);
  assert.match(lucky.attributes, /aria-pressed="true"/);
  assert.match(lucky.content, /<img\b[^>]*src="\/image\/ui\/rare"[^>]*alt=""/);
});

test("Pal soul enhancement and condensation render as separate upgrade sections", async () => {
  const html = await renderPalEditorFixture();

  assert.match(html, /<h2[^>]*>.*Enhance Pals<\/h2>/s);
  assert.match(html, /<h3[^>]*>.*Pal Condensation<\/h3>/s);
});
