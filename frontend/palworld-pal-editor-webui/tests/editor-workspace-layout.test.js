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

test("editor workspace owns independently persisted roster collapse state", async () => {
    const [app, view, topbar, players, pals] = await Promise.all([
        read("../src/App.vue"),
        read("../src/views/EditorView.vue"),
        read("../src/components/TopBar.vue"),
        read("../src/components/PlayerList.vue"),
        read("../src/components/PalList.vue"),
    ]);
    assert.match(app, /editor\.playersCollapsed/);
    assert.match(app, /editor\.palsCollapsed/);
    assert.match(app, /<TopBar[^>]*:players-collapsed="playersCollapsed"[^>]*:pals-collapsed="palsCollapsed"/s);
    assert.match(app, /<EditorView[^>]*:players-collapsed="playersCollapsed"[^>]*:pals-collapsed="palsCollapsed"/s);
    assert.match(view, /defineProps\(\{[\s\S]*playersCollapsed:[\s\S]*palsCollapsed:/);
    assert.match(view, /@toggle="emit\('collapsePlayers'\)"/);
    assert.match(view, /@toggle="emit\('collapsePals'\)"/);
    assert.match(topbar, /class="editor-roster-dock"/);
    assert.match(topbar, /class="editor-roster-preview/);
    assert.match(topbar, /@click="emit\('restorePlayers'\)"/);
    assert.match(topbar, /@click="emit\('restorePals'\)"/);
    assert.match(topbar, /\.editor-roster-dock:hover\s+\.editor-roster-preview/);
    assert.match(topbar, /\.editor-roster-preview:hover/);
    assert.match(topbar, /@keyframes roster-dock-in/);
    assert.match(topbar, /\.editor-roster-pill\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)/s);
    assert.match(topbar, /\.editor-roster-pill:hover\s*\{[^}]*background:\s*var\(--editor-color-glass-surface\)/s);
    assert.match(topbar, /\.editor-roster-dock::after\s*\{[^}]*top:\s*100%[^}]*height:\s*var\(--editor-space-2\)/s);
    assert.match(topbar, /class="editor-context-actions"/);
    assert.match(topbar, /\.editor-context-actions\s*\{[^}]*margin-left:\s*auto/s);
    assert.match(topbar, /\.editor-roster-preview\s*\{[^}]*visibility:\s*hidden[^}]*opacity:\s*0[^}]*border:\s*1px solid var\(--editor-color-glass-border\)/s);
    assert.doesNotMatch(topbar, /\.editor-roster-preview\s*\{[^}]*display:\s*none/s);
    assert.doesNotMatch(view, /editor-roster-launchers|editor-roster-launcher/);
    assert.match(players, /defineEmits\(\['toggle'\]\)/);
    assert.match(pals, /defineEmits\(\['toggle'\]\)/);
    for (const roster of [players, pals]) {
        assert.match(roster, /class="roster-collapse-button"[\s\S]*@click="emit\('toggle'\)"/);
        assert.match(roster, /<UiIcon :name="preview \? 'plus' : 'minus'"/);
        assert.match(roster, /class="roster-title"/);
        assert.doesNotMatch(roster, /roster-title[^>]*@click=/);
        assert.match(roster, /\.roster-title\s*\{[^}]*position:\s*absolute[^}]*top:\s*50%[^}]*left:\s*50%[^}]*transform:\s*translate\(-50%,\s*-50%\)/s);
        assert.match(roster, /\.roster-collapse-button\s*\{[^}]*border:\s*0[^}]*background:\s*transparent/s);
        assert.match(roster, /\.roster-collapse-button:hover\s*\{[^}]*background:\s*var\(--editor-color-control-hover\)/s);
    }
    assert.match(pals, /<header class="roster-header">\s*<div class="roster-heading-row">[\s\S]*?<\/div>\s*<label class="pal-search"/);
    assert.match(pals, /\.roster-heading-row\s*\{[^}]*position:\s*relative[^}]*min-height:\s*2rem/s);
    assert.doesNotMatch(pals, /\.roster-header\s*\{[^}]*position:\s*relative/s);
    assert.match(players, /PlayerList_Collapse/);
    assert.match(pals, /PalList_Collapse/);
    assert.match(players, /preview \? 'PlayerList_Restore' : 'PlayerList_Collapse'/);
    assert.match(pals, /preview \? 'PalList_Restore' : 'PalList_Collapse'/);
    assert.match(topbar, /<PlayerList preview/);
    assert.doesNotMatch(players, /unlock_viewing_cage|PlayerList_Viewing_Cage/);
    assert.match(view, /\.editor-workspace--pals-only\s*\{\s*grid-template-columns:\s*minmax\(15rem, 17rem\) minmax\(0, 1fr\)/);
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
    assert.match(pals, /import PalPortrait from/);
    assert.match(pals, /<PalPortrait[^>]*:src="palStore\.backendAssetUrl\(`\/image\/pals\/\$\{pal\.IconAccessKey\}`\)"[^>]*size="2\.5rem"/s);
    assert.match(pals, /<PalPortrait[^>]*alt=""/s);
    assert.match(pals, /<template #top-left>[\s\S]*?v-if="pal\.IsBOSS"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/boss'\)"/);
    assert.match(pals, /<template #top-left>[\s\S]*?v-else-if="pal\.IsRarePal"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/rare'\)"/);
    assert.match(pals, /<template #top-right>[\s\S]*?v-(?:else-)?if="pal\.IsBOSS && pal\.IsRarePal"[\s\S]*?:src="palStore\.backendAssetUrl\('\/image\/ui\/rare'\)"/);
    assert.doesNotMatch(players + pals, /\[selected|filter:\s*grayscale[^}]*selected/s);
});

test("new workspace labels are translated", () => {
    for (const locale of [en, fr, ja, zhCN]) {
        for (const key of ["TopBar_More", "PlayerList_Unknown", "PalList_Search", "PalList_Add", "Editor_Select_Prompt", "PlayerList_Collapse", "PlayerList_Restore", "PalList_Collapse", "PalList_Restore"]) {
            assert.equal(typeof locale[key], "string", key);
            assert.ok(locale[key].trim(), key);
        }
    }
});
