<script>
export function readRosterCollapsed(key) {
  try { return globalThis.localStorage.getItem(key) === 'true' }
  catch { return false }
}

export function persistRosterCollapsed(key, value) {
  try { globalThis.localStorage.setItem(key, String(value)) }
  catch { /* restricted storage keeps the in-memory state */ }
}
</script>

<script setup>
import { ref, watch } from 'vue'

import PalEditor from '@/components/PalEditor.vue'
import PalList from '@/components/PalList.vue'
import PlayerEditor from '@/components/PlayerEditor.vue'
import PlayerList from '@/components/PlayerList.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const playersCollapsed = ref(readRosterCollapsed('editor.playersCollapsed'))
const palsCollapsed = ref(readRosterCollapsed('editor.palsCollapsed'))
watch(playersCollapsed, value => persistRosterCollapsed('editor.playersCollapsed', value))
watch(palsCollapsed, value => persistRosterCollapsed('editor.palsCollapsed', value))
</script>

<template>
  <div class="editor-workspace" :class="{
    'editor-workspace--players-only': !playersCollapsed && palsCollapsed,
    'editor-workspace--pals-only': playersCollapsed && !palsCollapsed,
    'editor-workspace--canvas-only': playersCollapsed && palsCollapsed,
  }">
    <aside v-show="!playersCollapsed" class="editor-roster editor-roster--players">
      <PlayerList @collapse="playersCollapsed = true" />
    </aside>
    <aside v-show="!palsCollapsed" class="editor-roster editor-roster--pals">
      <PalList v-if="palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG" @collapse="palsCollapsed = true" />
    </aside>
    <main class="editor-canvas">
      <div class="editor-roster-launchers">
        <button v-if="playersCollapsed" class="editor-roster-launcher"
          :title="palStore.getTranslatedText('PlayerList_Restore')"
          :aria-label="palStore.getTranslatedText('PlayerList_Restore')" @click="playersCollapsed = false">
          <UiIcon name="back" />
        </button>
        <button v-if="palsCollapsed && (palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG)" class="editor-roster-launcher"
          :title="palStore.getTranslatedText('PalList_Restore')"
          :aria-label="palStore.getTranslatedText('PalList_Restore')" @click="palsCollapsed = false">
          <UiIcon name="back" />
        </button>
      </div>
      <PlayerEditor v-if="palStore.SHOW_PLAYER_EDIT_FLAG" />
      <PalEditor v-else-if="palStore.SELECTED_PAL_ID && palStore.SELECTED_PAL_DATA" />
      <p v-else class="editor-empty">{{ palStore.getTranslatedText('Editor_Select_Prompt') }}</p>
    </main>
  </div>
</template>

<style scoped>
.editor-workspace {
  display: grid;
  grid-template-columns: minmax(10rem, 11rem) minmax(15rem, 17rem) minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  height: 100%;
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  overflow: hidden;
}

.editor-workspace--players-only {
  grid-template-columns: minmax(10rem, 11rem) minmax(0, 1fr);
}

.editor-workspace--pals-only {
  grid-template-columns: minmax(15rem, 17rem) minmax(0, 1fr);
}

.editor-workspace--canvas-only {
  grid-template-columns: minmax(0, 1fr);
}

.editor-roster,
.editor-canvas {
  min-width: 0;
  min-height: 0;
}

.editor-roster {
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-glass-shadow);
}

.editor-canvas {
  position: relative;
  overflow: auto;
}

.editor-roster-launchers {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  gap: var(--editor-space-2);
}

.editor-roster-launcher {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  cursor: pointer;
}

.editor-roster-launcher:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

.editor-empty {
  display: grid;
  min-height: 12rem;
  place-items: center;
  color: var(--editor-color-muted);
}

@media (max-width: 760px) {
  .editor-workspace {
    display: flex;
    flex-direction: column;
    overflow: auto;
  }

  .editor-roster {
    flex: 0 0 auto;
    max-height: min(15rem, 32dvh);
  }

  .editor-canvas {
    flex: 0 0 auto;
    overflow: visible;
  }
}
</style>
