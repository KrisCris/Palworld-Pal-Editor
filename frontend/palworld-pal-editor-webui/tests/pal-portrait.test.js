import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { after } from "node:test";

import { h } from "vue";

import { closeVueServer, loadVueModule, renderVue } from "./vue-render.js";

after(closeVueServer);

test("PalPortrait renders caller sizing and all four marker slots", async () => {
  const { default: PalPortrait } = await loadVueModule("/src/components/PalPortrait.vue");
  const html = await renderVue(PalPortrait, {
    props: {
      src: "/image/pals/TestPal",
      alt: "Test Pal",
      size: "5.5rem",
      borderColor: "hotpink",
      glowColor: "gold",
    },
    slots: Object.fromEntries(
      ["top-left", "top-right", "bottom-left", "bottom-right"]
        .map(name => [name, () => h("b", { "data-marker": name }, name)]),
    ),
  });

  assert.match(html, /class="pal-portrait has-glow"/);
  assert.match(html, /style="--pal-portrait-size:5\.5rem;--pal-portrait-border:hotpink;--pal-portrait-glow:gold;"/);
  assert.match(html, /<img\b[^>]*src="\/image\/pals\/TestPal"[^>]*alt="Test Pal"/);
  for (const name of ["top-left", "top-right", "bottom-left", "bottom-right"]) {
    assert.match(html, new RegExp(`pal-portrait__marker--${name}[^>]*aria-hidden="true"[\\s\\S]*?data-marker="${name}"`));
  }
});

test("PalPortrait scales markers and supports the awakened glow", async () => {
  const source = await readFile(new URL("../src/components/PalPortrait.vue", import.meta.url), "utf8");
  assert.match(source, /clamp\(\.9rem,\s*36%,\s*2rem\)/);
  assert.match(source, /game-lucky-icon[\s\S]*scale\(1\.2\)/);
  assert.match(source, /game-dna-icon[\s\S]*scale\(1\.2\)/);
  assert.match(source, /\.has-glow\s+\.pal-portrait__image[\s\S]*box-shadow/);

  for (const component of ["PalEditor.vue", "PalList.vue"]) {
    const consumer = await readFile(new URL(`../src/components/${component}`, import.meta.url), "utf8");
    assert.match(consumer, /const portraitBorder = pal => pal\.IsAwakening/);
    assert.match(consumer, /:glow-color="[^\"]*IsAwakening/);
    assert.match(consumer, /class="game-lucky-icon"/);
    assert.doesNotMatch(consumer, /pal-corner-stack/);
  }

  assert.match(source, /pal-portrait__marker--bottom-left[^{]*\{[^}]*display:\s*flex[^}]*align-items:\s*center[^}]*justify-content:\s*center/s);
});

test("PalPortrait uses the compact default size", async () => {
  const { default: PalPortrait } = await loadVueModule("/src/components/PalPortrait.vue");
  const html = await renderVue(PalPortrait, { props: { src: "/image/pals/TestPal" } });
  assert.match(html, /--pal-portrait-size:2\.5rem/);
});
