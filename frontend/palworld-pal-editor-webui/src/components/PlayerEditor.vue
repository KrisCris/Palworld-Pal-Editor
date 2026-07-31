<script setup>
import { computed } from 'vue'

import TechCard from '@/components/modules/TechCard.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const playerName = () => palStore.SELECTED_PLAYER_DATA.NickName || palStore.getTranslatedText('PlayerList_Unknown')
const playerInitial = () => playerName().trim().charAt(0).toUpperCase() || '?'
const isMaxLv = () => palStore.SELECTED_PLAYER_DATA.Level >= (
  palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL
)
const isMinLv = () => palStore.SELECTED_PLAYER_DATA.Level <= 1
const fieldActionLabel = key => `${palStore.getTranslatedText('Editor_Apply_Change')}: ${palStore.getTranslatedText(key)}`
const technologyRows = computed(() => Object.entries(palStore.TECH_LV_DICT).map(([level, items]) => ({
  level,
  normal: items.filter(item => !item.BossTechnology),
  ancient: items.filter(item => item.BossTechnology),
})))
</script>

<template>
  <section class="player-editor">
    <header class="player-summary">
      <span class="player-summary__avatar">{{ playerInitial() }}</span>
      <div class="player-summary__identity">
        <small>{{ palStore.getTranslatedText('PlayerEditor_Title') }}</small>
        <h1>{{ playerName() }}</h1>
        <div class="player-summary__meta">
          <span>Lv. {{ palStore.SELECTED_PLAYER_DATA.Level }}</span>
          <span>{{ palStore.getTranslatedText('Editor_Exp') }} {{ palStore.SELECTED_PLAYER_DATA.Exp }}</span>
        </div>
      </div>
    </header>

    <div class="player-dashboard">
      <section class="player-panel">
        <h2>{{ palStore.getTranslatedText('Editor_Basic_Info') }}</h2>
        <div class="player-fields">
          <div class="player-field">
            <label for="player-name">{{ palStore.getTranslatedText('Editor_Nickname') }}</label>
            <div class="player-control">
              <input id="player-name" type="text" name="NickName" v-model="palStore.SELECTED_PLAYER_DATA.NickName">
              <button type="button" @click="palStore.updatePlayer" name="NickName"
                :value="palStore.SELECTED_PLAYER_DATA.NickName" :disabled="palStore.LOADING_FLAG"
                :aria-label="fieldActionLabel('Editor_Nickname')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="technology-points">{{ palStore.getTranslatedText('Editor_TechPoint') }}</label>
            <div class="player-control">
              <input id="technology-points" type="number" name="TechnologyPoint" min="0" max="65535"
                v-model="palStore.SELECTED_PLAYER_DATA.TechnologyPoint">
              <button type="button" @click="palStore.updatePlayer" name="TechnologyPoint"
                :value="palStore.SELECTED_PLAYER_DATA.TechnologyPoint" :disabled="palStore.LOADING_FLAG"
                :aria-label="fieldActionLabel('Editor_TechPoint')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="boss-technology-points">{{ palStore.getTranslatedText('Editor_BossTechPoint') }}</label>
            <div class="player-control">
              <input id="boss-technology-points" type="number" name="bossTechnologyPoint" min="0" max="65535"
                v-model="palStore.SELECTED_PLAYER_DATA.bossTechnologyPoint">
              <button type="button" @click="palStore.updatePlayer" name="bossTechnologyPoint"
                :value="palStore.SELECTED_PLAYER_DATA.bossTechnologyPoint" :disabled="palStore.LOADING_FLAG"
                :aria-label="fieldActionLabel('Editor_BossTechPoint')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="unused-status-points">{{ palStore.getTranslatedText('Editor_UnusedStatusPoints') }}</label>
            <div class="player-control">
              <input id="unused-status-points" type="number" name="UnusedStatusPoint" min="0" max="65535"
                v-model.number="palStore.SELECTED_PLAYER_DATA.UnusedStatusPoint">
              <button type="button" @click="palStore.updatePlayer" name="UnusedStatusPoint"
                :value="palStore.SELECTED_PLAYER_DATA.UnusedStatusPoint" :disabled="palStore.LOADING_FLAG"
                :aria-label="fieldActionLabel('Editor_UnusedStatusPoints')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field player-field--level">
            <span>Lv. {{ palStore.SELECTED_PLAYER_DATA.Level }}</span>
            <div class="level-controls">
              <button type="button" @click="palStore.SELECTED_PLAYER_DATA.levelDown" name="Level"
                :disabled="palStore.LOADING_FLAG || isMinLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Decrease')"><UiIcon name="minus" /></button>
              <button type="button" @click="palStore.SELECTED_PLAYER_DATA.levelUp" name="Level"
                :disabled="palStore.LOADING_FLAG || isMaxLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Increase')"><UiIcon name="plus" /></button>
              <button type="button" @click="palStore.SELECTED_PLAYER_DATA.maxLevel" name="Level"
                :disabled="palStore.LOADING_FLAG || isMaxLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Max')"><UiIcon name="maximum" /></button>
            </div>
          </div>
        </div>
      </section>

      <section class="player-panel" v-if="palStore.SELECTED_PLAYER_DATA.StatusPoints">
        <h2>{{ palStore.getTranslatedText('Editor_StatusUpgrades') }}</h2>
        <div class="status-grid">
          <div class="status-control" v-for="(points, name) in palStore.SELECTED_PLAYER_DATA.StatusPoints" :key="name">
            <label :for="`status-${name}`">{{ palStore.getTranslatedText(`StatusPoint_${name}`) }}</label>
            <div class="player-control">
              <input :id="`status-${name}`" type="number" min="0"
                :max="palStore.SELECTED_PLAYER_DATA.StatusPointMaximums[name]"
                v-model.number="palStore.SELECTED_PLAYER_DATA.StatusPoints[name]">
              <button type="button" @click="palStore.SELECTED_PLAYER_DATA.setStatusPoint(name)"
                :disabled="palStore.LOADING_FLAG"
                :aria-label="`${palStore.getTranslatedText('Editor_Apply_Change')}: ${palStore.getTranslatedText(`StatusPoint_${name}`)}`">
                <UiIcon name="check" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="player-panel technology-panel">
      <header class="technology-panel__header">
        <h2>{{ palStore.getTranslatedText('Editor_TechEdit') }}</h2>
        <button type="button" class="unlock-all" @click="palStore.updatePlayer" name="unlock_all_techs"
          :disabled="palStore.LOADING_FLAG">
          <UiIcon name="unlock" />
          {{ palStore.getTranslatedText('Editor_UnlockAllTech') }}
        </button>
      </header>

      <div class="technology-levels">
        <section class="technology-level" v-for="row in technologyRows" :key="row.level">
          <div class="technology-level__track"><h3>Lv. {{ row.level }}</h3></div>
          <div class="technology-lane technology-lane--normal">
            <TechCard v-for="item in row.normal" :key="item.InternalName" :item="item" />
          </div>
          <div class="technology-lane technology-lane--ancient" :class="{ 'is-empty': !row.ancient.length }">
            <TechCard v-for="item in row.ancient" :key="item.InternalName" :item="item" />
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<style scoped>
.player-editor {
  container-type: inline-size;
  display: grid;
  gap: var(--editor-space-3);
  min-width: 0;
  color: var(--editor-color-text);
}

.player-summary,
.player-panel {
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-surface-subtle);
}

.player-summary {
  display: flex;
  align-items: center;
  gap: var(--editor-space-3);
  padding: var(--editor-space-4);
}

.player-summary__avatar {
  display: grid;
  flex: 0 0 4rem;
  width: 4rem;
  height: 4rem;
  place-items: center;
  border-radius: 50%;
  color: var(--editor-color-text);
  background: var(--editor-color-primary);
  font-size: 1.5rem;
  font-weight: 700;
}

.player-summary__identity { min-width: 0; }
.player-summary__identity small {
  color: var(--editor-color-focus);
  font-size: .7rem;
  letter-spacing: .08em;
}

.player-summary h1 {
  margin: var(--editor-space-1) 0;
  overflow: hidden;
  font-size: clamp(1.25rem, 3cqi, 2rem);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-summary__meta { display: flex; flex-wrap: wrap; gap: var(--editor-space-2); }
.player-summary__meta span {
  padding: .15rem .55rem;
  border: 1px solid var(--editor-color-border);
  border-radius: 999px;
  color: var(--editor-color-muted);
  font-size: .75rem;
}

.player-dashboard {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: var(--editor-space-3);
}

.player-panel { min-width: 0; padding: var(--editor-space-4); }
.player-panel h2 {
  margin: 0 0 var(--editor-space-3);
  padding-bottom: var(--editor-space-2);
  border-bottom: 1px solid var(--editor-color-border);
  font-size: .9rem;
  font-weight: 600;
  text-transform: uppercase;
}

.player-fields,
.status-grid { display: grid; gap: var(--editor-space-2); }
.status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.player-field,
.status-control { min-width: 0; }
.player-field > label,
.status-control > label {
  display: block;
  margin-bottom: var(--editor-space-1);
  overflow: hidden;
  color: var(--editor-color-muted);
  font-size: .75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-control,
.level-controls { display: flex; min-width: 0; gap: var(--editor-space-1); }
.player-control input {
  width: 100%;
  min-width: 0;
  min-height: 2.35rem;
  padding: 0 var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.player-control button,
.level-controls button,
.unlock-all {
  display: inline-flex;
  min-height: 2.35rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  cursor: pointer;
}

.player-control button,
.level-controls button { flex: 0 0 2.35rem; width: 2.35rem; padding: 0; }
.player-control button:hover,
.level-controls button:hover,
.unlock-all:hover { color: var(--editor-color-background); background: var(--editor-color-primary); }
.player-control button:disabled,
.level-controls button:disabled,
.unlock-all:disabled { border-color: var(--editor-color-disabled); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); cursor: not-allowed; }

.player-control input:focus-visible,
.player-control button:focus-visible,
.level-controls button:focus-visible,
.unlock-all:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

.player-field--level {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--editor-space-2);
  border-top: 1px solid var(--editor-color-border);
}
.player-field--level > span { font-weight: 600; }

.technology-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-2);
  margin-bottom: var(--editor-space-3);
  padding-bottom: var(--editor-space-2);
  border-bottom: 1px solid var(--editor-color-border);
}
.technology-panel__header h2 { margin: 0; padding: 0; border: 0; }
.unlock-all { gap: var(--editor-space-1); padding: 0 var(--editor-space-3); color: var(--editor-color-background); background: var(--editor-color-primary); }
.technology-levels { display: grid; gap: var(--editor-space-3); }
.technology-level {
  display: grid;
  grid-template-columns: 4rem minmax(7.5rem, 1fr) minmax(7.5rem, 18rem);
  align-items: stretch;
  gap: var(--editor-space-2);
  min-height: 7.5rem;
}
.technology-level__track {
  position: relative;
  display: grid;
  place-items: start center;
}
.technology-level__track::before {
  position: absolute;
  top: 0;
  bottom: calc(var(--editor-space-3) * -1);
  width: 2px;
  background: var(--editor-color-focus);
  content: '';
}
.technology-level:last-child .technology-level__track::before { bottom: 50%; }
.technology-level__track h3 {
  z-index: 1;
  display: grid;
  width: 3.35rem;
  aspect-ratio: 1;
  place-items: center;
  margin: 0;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  color: var(--editor-color-background);
  background: var(--editor-color-focus);
  font-size: .8rem;
  font-weight: 700;
  text-align: center;
}
.technology-lane {
  display: flex;
  min-width: 0;
  align-content: flex-start;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--editor-space-2);
}
.technology-lane--ancient {
  padding: var(--editor-space-1);
  border-left: 2px solid var(--editor-color-ancient);
  border-radius: var(--editor-radius-sm);
  background: color-mix(in srgb, var(--editor-color-ancient) 9%, transparent);
}
.technology-lane--ancient.is-empty { opacity: .35; }

@container (max-width: 58rem) {
  .technology-level { grid-template-columns: 4rem minmax(0, 1fr); }
  .technology-level__track { grid-row: 1 / span 2; }
  .technology-lane--ancient { grid-column: 2; }
}

@container (max-width: 48rem) {
  .player-dashboard { grid-template-columns: 1fr; }
}

@container (max-width: 32rem) {
  .status-grid { grid-template-columns: 1fr; }
  .player-summary,
  .technology-panel__header { align-items: flex-start; }
  .technology-panel__header { flex-direction: column; }
  .technology-level { grid-template-columns: 3.5rem minmax(0, 1fr); }
}
</style>
