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

test("toolbar keeps all operations in global and contextual rows", async () => {
    const source = await read("../src/components/TopBar.vue");
    assert.match(source, /class="editor-app-bar"/);
    assert.match(source, /class="editor-context-bar"/);
    assert.match(source, /<details[^>]*class="editor-more"/);
    for (const handler of [
        "save", "palStore.loadSave", "palStore.reset", "palStore.updatePal",
        "palStore.SHOW_OOB_PAL_FLAG", "show_cheats", "palStore.SHOW_DONATE_FLAG",
        "palStore.updateI18n",
    ]) assert.match(source, new RegExp(handler.replaceAll(".", "\\.")), handler);
    assert.match(source, /@media\s*\(max-width:\s*480px\)[\s\S]*\.editor-app-bar\s*\{[^}]*display:\s*grid/);
    assert.match(source, /:aria-label="palStore\.getTranslatedText\('TopBar_Btn_Save'\)"/);
    assert.match(source, /:aria-label="palStore\.getTranslatedText\('TopBar_Btn_Reload'\)"/);
});

test("player and Pal rows preserve selection contracts without grayscale selection", async () => {
    const [players, pals] = await Promise.all([
        read("../src/components/PlayerList.vue"),
        read("../src/components/PalList.vue"),
    ]);
    assert.match(players, /:aria-current="player\.InstanceId == palStore\.SELECTED_PLAYER_ID \? 'true' : undefined"/);
    assert.match(players, /player\.NickName \|\| palStore\.getTranslatedText\('PlayerList_Unknown'\)/);
    assert.match(players, /\(player\.InstanceId == palStore\.SELECTED_PLAYER_ID && palStore\.SHOW_PLAYER_EDIT_FLAG\) \|\| palStore\.LOADING_FLAG/);
    assert.match(players, /palStore\.BASE_PAL_BTN_CLK_FLAG \|\| palStore\.LOADING_FLAG/);
    assert.match(pals, /:value="pal\.InstanceId"/);
    assert.match(pals, /:aria-current="palStore\.SELECTED_PAL_ID == pal\.InstanceId \? 'true' : undefined"/);
    assert.match(pals, /palStore\.SELECTED_PAL_ID == pal\.InstanceId \|\| palStore\.LOADING_FLAG/);
    assert.match(pals, /import \{ paldeckForRow \}/);
    assert.match(pals, /const paldeck = paldeckForRow\(row\)/);
    assert.match(pals, /v-if="pal\.IsRarePal"[^>]*:src="'\/image\/ui\/rare'"/);
    assert.match(pals, /v-if="pal\.IsBOSS"[^>]*:src="'\/image\/ui\/boss'"/);
    assert.doesNotMatch(players + pals, /\[selected|filter:\s*grayscale[^}]*selected/s);
});

test("new workspace labels are translated", () => {
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["TopBar_More", "PlayerList_Unknown", "PalList_Search", "PalList_Add", "Editor_Select_Prompt"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
