<script setup>
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const props = defineProps({ preview: Boolean })
const emit = defineEmits(['toggle'])
const toggleLabel = () => palStore.getTranslatedText(props.preview ? 'PlayerList_Restore' : 'PlayerList_Collapse')
const playerLabel = player => player.NickName || palStore.getTranslatedText('PlayerList_Unknown')
const playerInitial = player => playerLabel(player).trim().charAt(0).toUpperCase() || '?'
const globalRoster = () => palStore.SPECIAL_ROSTERS.find(roster => roster.Kind === 'global_palbox')
</script>

<template>
  <nav class="player-roster" :aria-label="palStore.getTranslatedText('PlayerList_Text')">
    <header class="roster-header">
      <button class="roster-collapse-button" :title="toggleLabel()"
        :aria-label="toggleLabel()" @click="emit('toggle')">
        <UiIcon :name="preview ? 'plus' : 'minus'" />
      </button>
      <h2 class="roster-title">{{ palStore.getTranslatedText("PlayerList_Text") }}</h2>
    </header>

    <div class="roster-list">
      <button v-if="globalRoster()" class="roster-row roster-row--global"
        @click="palStore.selectPlayer(palStore.PAL_GLOBAL_STORAGE_BTN)"
        :aria-current="palStore.SELECTED_PLAYER_ID === palStore.PAL_GLOBAL_STORAGE_BTN ? 'true' : undefined"
        :disabled="palStore.SELECTED_PLAYER_ID === palStore.PAL_GLOBAL_STORAGE_BTN || palStore.LOADING_FLAG">
        <span class="player-avatar">GPS</span>
        <span class="roster-copy">{{ palStore.getTranslatedText('Editor_Container_GlobalPalbox') }}</span>
      </button>

      <button v-if="palStore.HAS_WORKING_PAL_FLAG" class="roster-row roster-row--base"
        @click="palStore.selectPlayer(palStore.PAL_BASE_WORKER_BTN)"
        :aria-current="palStore.BASE_PAL_BTN_CLK_FLAG ? 'true' : undefined"
        :disabled="palStore.BASE_PAL_BTN_CLK_FLAG || palStore.LOADING_FLAG">
        <span class="player-avatar">PAL</span>
        <span class="roster-copy">{{ palStore.getTranslatedText('PlayerList_Base_Pal') }}</span>
      </button>

      <button v-for="player in palStore.PLAYER_MAP.values()" :key="player.InstanceId"
        class="roster-row" @click="palStore.selectPlayer(player.InstanceId)" :title="player.InstanceId"
        :aria-current="player.InstanceId == palStore.SELECTED_PLAYER_ID ? 'true' : undefined"
        :disabled="(player.InstanceId == palStore.SELECTED_PLAYER_ID && palStore.SHOW_PLAYER_EDIT_FLAG) || palStore.LOADING_FLAG">
        <span class="player-avatar">{{ playerInitial(player) }}</span>
        <span class="roster-copy">{{ player.NickName || palStore.getTranslatedText('PlayerList_Unknown') }}</span>
      </button>
    </div>
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
