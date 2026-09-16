import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import en from "../src/i18n/en.js";
import fr from "../src/i18n/fr.js";
import ja from "../src/i18n/ja.js";
import zhCN from "../src/i18n/zh-CN.js";

const read = path => readFile(new URL(path, import.meta.url), "utf8");

test("editor workspace uses bounded three-column rails and a scrolling canvas", async () => {
    const [view, app, base, main] = await Promise.all([
        read("../src/views/EditorView.vue"),
        read("../src/App.vue"),
        read("../src/assets/base.css"),
        read("../src/assets/main.css"),
    ]);
    assert.match(view, /class="editor-workspace"/);
    assert.match(view, /class="editor-roster editor-roster--players"/);
    assert.match(view, /class="editor-roster editor-roster--pals"/);
    assert.match(view, /class="editor-canvas"/);
    assert.match(view, /grid-template-columns:\s*minmax\(10rem, 11rem\)\s+minmax\(15rem, 17rem\)\s+minmax\(0, 1fr\)/);
    assert.match(view, /@media\s*\(max-width:\s*760px\)/);
    assert.match(view, /max-height:\s*min\(/);
    assert.match(base, /box-sizing:\s*border-box/);
    assert.match(app, /height:\s*100dvh/);
    assert.match(main, /html,\s*body,\s*#app\s*\{[^}]*height:\s*100%/s);
    assert.doesNotMatch(main, /body,\s*html\s*\{[^}]*display:\s*flex/s);
    assert.doesNotMatch(base, /--editor-panel-width|--sub-height/);
    assert.doesNotMatch(view, /100vw|calc\(100vw/);
});

test("new workspace labels are translated", () => {
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["PlayerList_Unknown", "PalList_Search", "PalList_Add", "Editor_Select_Prompt", "PlayerList_Collapse", "PlayerList_Restore", "PalList_Collapse", "PalList_Restore"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
