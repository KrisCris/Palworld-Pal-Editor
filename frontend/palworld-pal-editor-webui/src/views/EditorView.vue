<script setup>
import PalEditor from '@/components/PalEditor.vue'
import PalList from '@/components/PalList.vue'
import PlayerEditor from '@/components/PlayerEditor.vue'
import BaseCampEditor from '@/components/BaseCampEditor.vue'
import PlayerList from '@/components/PlayerList.vue'
import OverlayScrollArea from '@/components/modules/OverlayScrollArea.vue'
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { usePalsStore } from '@/stores/pals'
import { usePlayersStore } from '@/stores/players'
import { BASE_ROSTER_KEY, useRostersStore } from '@/stores/rosters'

const appStore = useAppStore()
const palsStore = usePalsStore()
const playersStore = usePlayersStore()
const rostersStore = useRostersStore()
// The base camp has no player page, so its canvas is the research editor until a
// worker is picked out of the list.
const baseCampOpen = computed(() => rostersStore.activeRosterKey === BASE_ROSTER_KEY
  && !palsStore.selectedRecordKey)
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
      <PalList v-if="rostersStore.activeRosterKey" @toggle="emit('collapsePals')" />
    </aside>
    <main class="editor-canvas" :class="{ 'editor-canvas--basecamp': baseCampOpen }">
      <OverlayScrollArea v-if="playersStore.showPlayerEditor">
        <div class="editor-canvas__viewport overlay-scroll-area__viewport">
          <PlayerEditor />
        </div>
      </OverlayScrollArea>
      <BaseCampEditor v-else-if="baseCampOpen" />
      <OverlayScrollArea v-else-if="palsStore.selectedPalLoaded">
        <div class="editor-canvas__viewport overlay-scroll-area__viewport">
          <PalEditor />
        </div>
      </OverlayScrollArea>
      <p v-else class="editor-empty">{{ appStore.getTranslatedText('Editor_Select_Prompt') }}</p>
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
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  box-shadow: var(--editor-glass-shadow);
  animation: roster-rail-enter .2s ease-out;
}

.editor-roster::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  border-radius: inherit;
  content: '';
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  pointer-events: none;
}

.editor-roster--players {
  z-index: 1;
}

.editor-roster--pals {
  z-index: 2;
  overflow: visible;
}

.editor-canvas {
  position: relative;
  isolation: isolate;
  overflow: hidden;
}

.editor-canvas__viewport {
  overflow-y: auto;
  overflow-x: hidden;
}

.editor-canvas--basecamp {
  overflow: hidden;
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

@media (min-width: 761px) and (max-width: 1180px) {
  .editor-canvas--basecamp {
    overflow: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .editor-roster { animation: none; }
}
</style>
