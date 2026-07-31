<script setup>
import PalEditor from '@/components/PalEditor.vue'
import PalList from '@/components/PalList.vue'
import PlayerEditor from '@/components/PlayerEditor.vue'
import PlayerList from '@/components/PlayerList.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
</script>

<template>
  <div class="editor-workspace">
    <aside class="editor-roster editor-roster--players">
      <PlayerList />
    </aside>
    <aside class="editor-roster editor-roster--pals">
      <PalList v-if="palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG" />
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

.editor-roster,
.editor-canvas {
  min-width: 0;
  min-height: 0;
}

.editor-roster {
  overflow: hidden;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-surface-subtle);
}

.editor-canvas {
  overflow: auto;
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
