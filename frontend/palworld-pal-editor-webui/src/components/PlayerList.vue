<script setup>
import OverlayScrollArea from '@/components/modules/OverlayScrollArea.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { useAppStore } from '@/stores/app'
import { usePalEditorStore } from '@/stores/paleditor'
import { usePalsStore } from '@/stores/pals'
import { usePlayersStore } from '@/stores/players'
import { BASE_ROSTER_KEY, GLOBAL_PALBOX_ROSTER_KEY, useRostersStore } from '@/stores/rosters'

const appStore = useAppStore()
const palStore = usePalEditorStore()
const palsStore = usePalsStore()
const playersStore = usePlayersStore()
const rostersStore = useRostersStore()
const props = defineProps({ preview: Boolean })
const emit = defineEmits(['toggle'])
const toggleLabel = () => appStore.getTranslatedText(props.preview ? 'PlayerList_Restore' : 'PlayerList_Collapse')
const playerLabel = player => player.NickName || appStore.getTranslatedText('PlayerList_Unknown')
const playerInitial = player => playerLabel(player).trim().charAt(0).toUpperCase() || '?'
</script>

<template>
  <nav class="player-roster" :aria-label="appStore.getTranslatedText('PlayerList_Text')">
    <header class="roster-header">
      <button class="roster-collapse-button" :title="toggleLabel()"
        :aria-label="toggleLabel()" @click="emit('toggle')">
        <UiIcon :name="preview ? 'panel' : 'minus'" />
      </button>
      <h2 class="roster-title">{{ appStore.getTranslatedText("PlayerList_Text") }}</h2>
    </header>

    <OverlayScrollArea>
    <div class="roster-list overlay-scroll-area__viewport">
      <button v-if="rostersStore.globalPalboxRoster" class="roster-row roster-row--global"
        @click="rostersStore.selectRoster(GLOBAL_PALBOX_ROSTER_KEY)"
        :aria-current="rostersStore.activeRosterKey === GLOBAL_PALBOX_ROSTER_KEY ? 'true' : undefined"
        :disabled="rostersStore.activeRosterKey === GLOBAL_PALBOX_ROSTER_KEY">
        <span class="player-avatar">GPS</span>
        <span class="roster-copy">{{ appStore.getTranslatedText('Editor_Container_GlobalPalbox') }}</span>
      </button>

      <button v-if="palStore.HAS_WORKING_PAL_FLAG" class="roster-row roster-row--base"
        @click="rostersStore.selectRoster(BASE_ROSTER_KEY)"
        :aria-current="rostersStore.activeRosterKey === BASE_ROSTER_KEY ? 'true' : undefined"
        :disabled="(rostersStore.activeRosterKey === BASE_ROSTER_KEY && !palsStore.selectedRecordKey)">
        <span class="player-avatar">PAL</span>
        <span class="roster-copy">{{ appStore.getTranslatedText('PlayerList_Base_Pal') }}</span>
      </button>

      <button v-for="player in playersStore.players" :key="player.InstanceId"
        class="roster-row" @click="rostersStore.selectRoster(`player:${player.InstanceId}`)" :title="player.InstanceId"
        :aria-current="player.InstanceId == rostersStore.activePlayerUid ? 'true' : undefined"
        :disabled="(player.InstanceId == rostersStore.activePlayerUid && playersStore.showPlayerEditor)">
        <span class="player-avatar">{{ playerInitial(player) }}</span>
        <span class="roster-copy">{{ player.NickName || appStore.getTranslatedText('PlayerList_Unknown') }}</span>
      </button>
    </div>
    </OverlayScrollArea>
  </nav>
</template>

<style scoped>
.player-roster {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}

.roster-header {
  position: relative;
  display: grid;
  min-height: 3.5rem;
  grid-template-columns: 2rem minmax(0, 1fr) 2rem;
  align-items: center;
  padding: var(--editor-space-3) var(--editor-space-2);
  border-bottom: 1px solid var(--editor-color-border);
}

.roster-title {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--editor-color-muted);
  font-size: .8rem;
  font-weight: 400;
  line-height: 1.2;
  letter-spacing: .04em;
  text-align: center;
  text-transform: uppercase;
  white-space: normal;
}

.roster-collapse-button {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-muted);
  background: transparent;
  cursor: pointer;
  transition: color .15s ease, background-color .15s ease;
}

.roster-collapse-button:hover {
  color: var(--editor-color-text);
  background: var(--editor-color-control-hover);
}

.roster-list {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  align-content: start;
  gap: var(--editor-space-1);
  overflow-y: auto;
  padding: var(--editor-space-2);
}

.roster-row {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  align-items: center;
  gap: var(--editor-space-2);
  min-height: 2.75rem;
  padding: var(--editor-space-1) var(--editor-space-2);
  border: 1px solid transparent;
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
  text-align: left;
  cursor: pointer;
}

.roster-row:hover {
  background: var(--editor-color-control-hover);
}

.roster-row[aria-current="true"] {
  border-color: var(--editor-color-focus);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
  box-shadow: inset .2rem 0 var(--editor-color-focus), 0 0 .7rem color-mix(in srgb, var(--editor-color-focus) 25%, transparent);
}

.roster-row:disabled {
  cursor: default;
}

.roster-copy {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-avatar {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 50%;
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
  font-size: .7rem;
  font-weight: 700;
}

.roster-row--base .player-avatar,
.roster-row--global .player-avatar {
  font-size: .55rem;
}

.roster-row--base .player-avatar {
  background: var(--editor-color-warning);
}

.roster-row--global .player-avatar {
  background: var(--editor-color-dna);
}

.roster-row:focus-visible,
.roster-collapse-button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@media (max-width: 760px) {
  .roster-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 480px) {
  .roster-list {
    grid-template-columns: 1fr;
  }
}
</style>
