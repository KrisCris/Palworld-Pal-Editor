import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { moveRecentFocus } from "../src/components/backend-server-selector-keys.js";

const read = path => readFile(new URL(path, import.meta.url), "utf8");

test("backend selector is available before the language control outside the editor", async () => {
    const topBar = await read("../src/components/TopBar.vue");

    assert.match(topBar, /import BackendServerSelector from ['"]\.\/BackendServerSelector\.vue['"]/);
    assert.match(topBar, /<BackendServerSelector v-if="sessionStore\.appState !== 'editor'"\s*\/>[\s\S]*<label class="language-control">/);
});

test("startup backend errors leave the server selector toolbar interactive", async () => {
    const errorView = await read("../src/views/BackendErrorView.vue");

    assert.match(errorView, /\.error-layer\.startup\s*\{[^}]*z-index:\s*10;/s);
});

test("backend selector exposes an accessible, dismissible connection popover", async () => {
    const source = await read("../src/components/BackendServerSelector.vue");

    for (const contract of [
        'UiIcon name="server"',
        'aria-expanded',
        'aria-controls',
        'BackendSelector_Label',
        'BackendSelector_Connected',
        'BackendSelector_Disconnected',
        'BackendSelector_Recent',
        'BackendSelector_Current',
        'BackendSelector_Remove',
        'BackendSelector_Other',
        'BackendSelector_Use_Page_Server',
        'BackendSelector_Invalid_Address',
        'BackendSelector_Connection_Failed',
        'palStore.connectBackend',
        'keydown',
        'pointerdown',
        'onBeforeUnmount',
        '@media (max-width: 760px)',
    ]) assert.ok(source.includes(contract), contract);
    assert.match(source, /role="menu"/);
    assert.match(source, /<li[^>]*role="none"/);
    assert.match(source, /class="backend-selector__recent-action"[^>]*@click="useBackend\(origin\)"/);
    assert.match(source, /class="backend-selector__recent-remove"/);
    assert.match(source, /\.backend-selector__recent-remove\s*\{[^}]*width:\s*2\.25rem/s);
    assert.match(source, /\.backend-selector__recent-action\s*\{[^}]*flex:\s*1/s);
    assert.match(source, /class="backend-selector__recent-remove"[^>]*role="menuitem"[^>]*@keydown="onRecentKeyDown"/s);
    assert.match(source, /@click\.stop="removeRecent\(origin\)"/);
    assert.doesNotMatch(source, /recentActions/);
    assert.match(source, /currentTarget\.closest\('\[role="menu"\]'\)\.querySelectorAll\('\[role="menuitem"\]:not\(:disabled\)'\)/);
    assert.match(source, /const triggerLabel = computed\([\s\S]*candidateOrigin\.value[\s\S]*backend\.BACKEND_CONNECTED/);
    assert.match(source, /:aria-label="triggerLabel"/);
    assert.match(source, /--backend-selector-popover-top/);
    assert.match(source, /class="backend-selector__header"/);
    assert.match(source, /class="backend-selector__current"/);
    assert.match(source, /class="backend-selector__connect-row"/);
    assert.match(source, /class="editor-button editor-button--primary"/);
    assert.match(source, /class="backend-selector__page-server"/);
    assert.match(source, /if \(await palStore\.connectBackend\(origin\)\) close\(true\)[\s\S]*else errorKey\.value = 'BackendSelector_Connection_Failed'/);
    assert.doesNotMatch(source, /window\.location\.protocol/);
    assert.doesNotMatch(source, /BackendSelector_Mixed_Content/);
    assert.match(source, /const visibleRecent = computed\(\(\) => backend\.BACKEND_RECENT\.filter\(origin => origin !== currentOrigin\.value\)\)/);
    assert.doesNotMatch(source, /class="op(?:\s|"|-)/);
    assert.match(source, /@media \(max-width: 760px\)[\s\S]*\.backend-selector__popover\s*\{[^}]*position:\s*fixed;[^}]*right:\s*var\(--editor-space-3\);[^}]*width:\s*min\(44rem,/);
});

test("recent server keyboard navigation moves between server actions", () => {
    const focused = [];
    const actions = [0, 1, 2].map(index => ({ focus: () => focused.push(index) }));
    const event = (key, currentTarget) => ({ key, currentTarget, prevented: false, preventDefault() { this.prevented = true } });

    const down = event("ArrowDown", actions[0]);
    assert.equal(moveRecentFocus(down, actions), true);
    assert.equal(down.prevented, true);
    assert.deepEqual(focused, [1]);

    const up = event("ArrowUp", actions[0]);
    assert.equal(moveRecentFocus(up, actions), true);
    assert.deepEqual(focused, [1, 2]);

    const enter = event("Enter", actions[1]);
    assert.equal(moveRecentFocus(enter, actions), false);
    assert.equal(enter.prevented, false);
});
