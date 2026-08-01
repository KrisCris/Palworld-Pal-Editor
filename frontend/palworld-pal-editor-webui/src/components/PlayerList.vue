<script setup>
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const emit = defineEmits(['collapse'])
const playerLabel = player => player.NickName || palStore.getTranslatedText('PlayerList_Unknown')
const playerInitial = player => playerLabel(player).trim().charAt(0).toUpperCase() || '?'
</script>

<template>
  <nav class="player-roster" :aria-label="palStore.getTranslatedText('PlayerList_Text')">
    <header class="roster-header">
      <h2>{{ palStore.getTranslatedText("PlayerList_Text") }}</h2>
      <div class="roster-actions">
        <button class="roster-icon-button" :title="palStore.getTranslatedText('PlayerList_Collapse')"
          :aria-label="palStore.getTranslatedText('PlayerList_Collapse')" @click="emit('collapse')">
          <UiIcon name="back" />
        </button>
        <button class="roster-icon-button"
          v-if="palStore.SELECTED_PLAYER_ID != null && !palStore.PLAYER_MAP.get(palStore.SELECTED_PLAYER_ID)?.HasViewingCage"
          :title="palStore.getTranslatedText('PlayerList_Viewing_Cage')"
          :aria-label="palStore.getTranslatedText('PlayerList_Viewing_Cage')"
          :disabled="palStore.LOADING_FLAG" @click="palStore.updatePlayer" name="unlock_viewing_cage">
          <UiIcon name="unlock" />
        </button>
      </div>
    </header>

    <div class="roster-list">
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-2);
  padding: var(--editor-space-3);
  border-bottom: 1px solid var(--editor-color-border);
}

.roster-header h2 {
  margin: 0;
  color: var(--editor-color-muted);
  font-size: .8rem;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.roster-actions {
  display: flex;
  gap: var(--editor-space-1);
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

.roster-row--base .player-avatar {
  background: var(--editor-color-warning);
  font-size: .55rem;
}

.roster-icon-button {
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

.roster-row:focus-visible,
.roster-icon-button:focus-visible {
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
