<script setup>
import PalEditor from '@/components/PalEditor.vue'
import PalList from '@/components/PalList.vue'
import PlayerEditor from '@/components/PlayerEditor.vue'
import PlayerList from '@/components/PlayerList.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
defineProps({ playersCollapsed: Boolean, palsCollapsed: Boolean })
const emit = defineEmits(['collapsePlayers', 'collapsePals'])
</script>

<template>
  <div class="editor-workspace" :class="{
    'editor-workspace--players-only': !playersCollapsed && palsCollapsed,
    'editor-workspace--pals-only': playersCollapsed && !palsCollapsed,
    'editor-workspace--canvas-only': playersCollapsed && palsCollapsed,
  }">
    <aside v-if="!playersCollapsed" class="editor-roster editor-roster--players">
      <PlayerList @toggle="emit('collapsePlayers')" />
    </aside>
    <aside v-if="!palsCollapsed" class="editor-roster editor-roster--pals">
      <PalList v-if="palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG" @toggle="emit('collapsePals')" />
    </aside>
    <main class="editor-canvas">
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
  animation: roster-rail-enter .2s ease-out;
}

.editor-canvas {
  position: relative;
  overflow: auto;
}

@keyframes roster-rail-enter {
  from { opacity: .5; transform: translate(-1rem, -1rem) scale(.96); }
  to { opacity: 1; transform: none; }
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

@media (prefers-reduced-motion: reduce) {
  .editor-roster { animation: none; }
}
</style>
