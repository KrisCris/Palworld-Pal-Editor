import assert from "node:assert/strict";
import test, { after } from "node:test";

import { h } from "vue";

import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

after(closeVueServer);

test("PalPortrait renders caller sizing and all four marker slots", async () => {
  const { default: PalPortrait } = await loadVueModule("/src/components/modules/PalPortrait.vue");
  const html = await renderVue(PalPortrait, {
    props: {
      src: "/image/pals/TestPal",
      alt: "Test Pal",
      size: "5.5rem",
      borderColor: "hotpink",
    },
    slots: Object.fromEntries(
      ["top-left", "top-right", "bottom-left", "bottom-right"]
        .map(name => [name, () => h("b", { "data-marker": name }, name)]),
    ),
  });

  assert.match(html, /style="--pal-portrait-size:5\.5rem;--pal-portrait-border:hotpink;"/);
  assert.match(html, /<img\b[^>]*src="\/image\/pals\/TestPal"[^>]*alt="Test Pal"/);
  for (const name of ["top-left", "top-right", "bottom-left", "bottom-right"]) {
    assert.match(html, new RegExp(`pal-portrait__marker--${name}[^>]*aria-hidden="true"[\\s\\S]*?data-marker="${name}"`));
  }
});

test("PalPortrait uses the compact default size", async () => {
  const { default: PalPortrait } = await loadVueModule("/src/components/modules/PalPortrait.vue");
  const html = await renderVue(PalPortrait, { props: { src: "/image/pals/TestPal" } });
  assert.match(html, /--pal-portrait-size:2\.5rem/);
});
