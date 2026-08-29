<script>
const clamp = (minimum, maximum, value) => Math.min(maximum, Math.max(minimum, value))

export function previewStatAllocation(player, name, target) {
  const stat = Math.max(0, Number(player.StatusPoints?.[name]) || 0)
  const item = Math.max(0, Number(player.ExStatusPoints?.[name]) || 0)
  const maximum = Math.max(0, Number(player.StatusPointTotalMaximums?.[name]) || 0)
  const total = clamp(0, maximum, Number(target) || 0)
  const change = total - stat - item

  if (change < 0) {
    const refunded = Math.min(stat, -change)
    return {
      stat: stat - refunded,
      item: item - (-change - refunded),
      unused: Math.max(0, Number(player.UnusedStatusPoint) || 0) + refunded,
      total,
    }
  }

  const unused = Math.max(0, Number(player.UnusedStatusPoint) || 0)
  const spent = Math.min(unused, change)
  return { stat: stat + spent, item: item + change - spent, unused: unused - spent, total }
}
</script>

<script setup>
import { computed, ref } from 'vue'

import PlayerInventory from '@/components/PlayerInventory.vue'
import SegmentedRange from '@/components/modules/SegmentedRange.vue'
import NumberStepper from '@/components/modules/NumberStepper.vue'
import TechCard from '@/components/modules/TechCard.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { useCatalogsStore } from '@/stores/catalogs'
import { usePalEditorStore } from '@/stores/paleditor'
import { usePlayersStore } from '@/stores/players'

const catalogsStore = useCatalogsStore()
const palStore = usePalEditorStore()
const playersStore = usePlayersStore()
const player = computed(() => playersStore.selectedPlayer)
const activeTab = ref('character')
const playerName = () => player.value.NickName || palStore.getTranslatedText('PlayerList_Unknown')
const playerInitial = () => playerName().trim().charAt(0).toUpperCase() || '?'
const isMaxLv = () => player.value.Level >= (
  palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL
)
const isMinLv = () => player.value.Level <= 1
const fieldActionLabel = key => `${palStore.getTranslatedText('Editor_Apply_Change')}: ${palStore.getTranslatedText(key)}`
const statusEntries = category => Object.entries(player.value.StatusPointMetadata || {})
  .filter(([, metadata]) => metadata.category === category)
const playerStats = computed(() => statusEntries('stat'))
const effigyAbilities = computed(() => statusEntries('effigy'))
const statAllocation = name => previewStatAllocation(
  player.value,
  name,
  player.value.StatusPointTotals[name],
)
const statusEffect = (name, metadata) => {
  const rank = player.value.StatusPointTotals[name] || 0
  const value = metadata.values?.[rank] ?? rank
  return `+${Number.isInteger(value) ? value : Number(value).toFixed(1)}${metadata.unit === 'percent' ? '%' : ''}`
}
const technologyRows = computed(() => Object.entries(catalogsStore.technologiesByLevel).map(([level, items]) => ({
  level,
  normal: items.filter(item => !item.BossTechnology),
  ancient: items.filter(item => item.BossTechnology),
})))
</script>

<template>
  <div class="player-editor-shell">
  <section class="player-editor" :class="{ 'player-editor--items': activeTab === 'items' }">
    <header class="player-summary">
      <span class="player-summary__avatar">{{ playerInitial() }}</span>
      <div class="player-summary__identity">
        <small>{{ palStore.getTranslatedText('PlayerEditor_Title') }}</small>
        <h1>{{ playerName() }}</h1>
        <div class="player-summary__meta">
          <span>Lv. {{ player.Level }}</span>
          <span>{{ palStore.getTranslatedText('Editor_Exp') }} {{ player.Exp }}</span>
        </div>
      </div>
    </header>

    <nav class="player-tabs" :aria-label="palStore.getTranslatedText('PlayerEditor_Title')">
      <button type="button" :class="{ active: activeTab === 'character' }" @click="activeTab = 'character'">
        {{ palStore.getTranslatedText('PlayerEditor_Character') }}
      </button>
      <button type="button" :class="{ active: activeTab === 'items' }" @click="activeTab = 'items'">
        {{ palStore.getTranslatedText('PlayerEditor_Items') }}
      </button>
    </nav>

    <div v-if="activeTab === 'character'" class="player-character">
    <div class="player-dashboard">
      <section class="player-panel">
        <h2>{{ palStore.getTranslatedText('Editor_Basic_Info') }}</h2>
        <div class="player-fields">
          <div class="player-field">
            <label for="player-name">{{ palStore.getTranslatedText('Editor_Nickname') }}</label>
            <div class="player-control">
              <input id="player-name" type="text" name="NickName" v-model="player.NickName">
              <button type="button" @click="palStore.updatePlayer" name="NickName"
                :value="player.NickName"
                :aria-label="fieldActionLabel('Editor_Nickname')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="technology-points">{{ palStore.getTranslatedText('Editor_TechPoint') }}</label>
            <div class="player-control">
              <NumberStepper id="technology-points" name="TechnologyPoint" :min="0" :max="65535"
                :label="palStore.getTranslatedText('Editor_TechPoint')"
                v-model="player.TechnologyPoint" />
              <button type="button" @click="palStore.updatePlayer" name="TechnologyPoint"
                :value="player.TechnologyPoint"
                :aria-label="fieldActionLabel('Editor_TechPoint')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="boss-technology-points">{{ palStore.getTranslatedText('Editor_BossTechPoint') }}</label>
            <div class="player-control">
              <NumberStepper id="boss-technology-points" name="bossTechnologyPoint" :min="0" :max="65535"
                :label="palStore.getTranslatedText('Editor_BossTechPoint')"
                v-model="player.bossTechnologyPoint" />
              <button type="button" @click="palStore.updatePlayer" name="bossTechnologyPoint"
                :value="player.bossTechnologyPoint"
                :aria-label="fieldActionLabel('Editor_BossTechPoint')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field">
            <label for="unused-status-points">{{ palStore.getTranslatedText('Editor_UnusedStatusPoints') }}</label>
            <div class="player-control">
              <NumberStepper id="unused-status-points" name="UnusedStatusPoint" :min="0" :max="65535"
                :label="palStore.getTranslatedText('Editor_UnusedStatusPoints')"
                v-model="player.UnusedStatusPoint" />
              <button type="button" @click="palStore.updatePlayer" name="UnusedStatusPoint"
                :value="player.UnusedStatusPoint"
                :aria-label="fieldActionLabel('Editor_UnusedStatusPoints')"><UiIcon name="check" /></button>
            </div>
          </div>

          <div class="player-field player-field--level">
            <span>Lv. {{ player.Level }}</span>
            <div class="level-controls">
              <button type="button" @click="palStore.playerLevelDown" name="Level"
                :disabled="isMinLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Decrease')"><UiIcon name="minus" /></button>
              <button type="button" @click="palStore.playerLevelUp" name="Level"
                :disabled="isMaxLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Increase')"><UiIcon name="plus" /></button>
              <button type="button" @click="palStore.playerMaxLevel" name="Level"
                :disabled="isMaxLv()"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Max')"><UiIcon name="maximum" /></button>
            </div>
          </div>
        </div>
      </section>

      <section class="player-panel player-stats" v-if="player.StatusPointMetadata">
        <header class="status-panel__header">
          <h2>{{ palStore.getTranslatedText('Editor_PlayerStats') }}</h2>
          <div class="status-legend">
            <span class="status-legend__stat">{{ palStore.getTranslatedText('Editor_StatPoints') }}</span>
            <span class="status-legend__item">{{ palStore.getTranslatedText('Editor_ItemLevel') }}</span>
          </div>
        </header>
        <div class="status-grid">
          <article class="status-control" v-for="([name, metadata]) in playerStats" :key="name">
            <header>
              <span class="status-name">
                <img :src="palStore.backendAssetUrl(`/image/ui/${metadata.icon}`)" alt="">
                {{ palStore.getTranslatedText(`StatusPoint_${name}`) }}
              </span>
              <strong class="status-allocation">
                {{ statAllocation(name).total }} / {{ player.StatusPointTotalMaximums[name] }}
                (<span class="status-allocation__stat">{{ statAllocation(name).stat }}</span>+<span class="status-allocation__item">{{ statAllocation(name).item }}</span>)
              </strong>
            </header>
            <SegmentedRange :name="`status-${name}`" :min="0"
              :max="player.StatusPointTotalMaximums[name]"
              :segments="[
                { role: 'item', value: statAllocation(name).item },
                { role: 'primary', value: statAllocation(name).stat },
              ]"
              :thumb-role="statAllocation(name).stat ? 'primary' : 'item'"
              v-model="player.StatusPointTotals[name]"
              :aria-label="palStore.getTranslatedText(`StatusPoint_${name}`)"
              @change="palStore.setStatusPoint(name)" />
            <footer>
              <span>{{ palStore.getTranslatedText('Editor_Effect') }}</span>
              <strong>{{ statusEffect(name, metadata) }}</strong>
            </footer>
          </article>
        </div>
      </section>
    </div>

    <section class="player-panel effigy-panel" v-if="effigyAbilities.length">
      <h2>{{ palStore.getTranslatedText('Editor_EffigyAbilities') }}</h2>
      <div class="effigy-grid">
        <article class="status-control" v-for="([name, metadata]) in effigyAbilities" :key="name">
          <header>
            <span class="status-name">
              <img :src="palStore.backendAssetUrl(`/image/ui/${metadata.icon}`)" alt="">
              {{ palStore.getTranslatedText(`StatusPoint_${name}`) }}
            </span>
            <strong>{{ player.StatusPointTotals[name] }} / {{ player.StatusPointTotalMaximums[name] }}</strong>
          </header>
          <SegmentedRange :name="`status-${name}`" :min="0"
            :max="player.StatusPointTotalMaximums[name]"
            v-model="player.StatusPointTotals[name]"
            :aria-label="palStore.getTranslatedText(`StatusPoint_${name}`)"
            @change="palStore.setStatusPoint(name)" />
          <footer>
            <span>{{ palStore.getTranslatedText('Editor_Effect') }}</span>
            <strong>{{ statusEffect(name, metadata) }}</strong>
          </footer>
        </article>
      </div>
    </section>

    <section class="player-panel technology-panel">
      <header class="technology-panel__header">
        <h2>{{ palStore.getTranslatedText('Editor_TechEdit') }}</h2>
        <button type="button" class="unlock-all" @click="palStore.unlockAllTechs">
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
    </div>
    <PlayerInventory v-else />
  </section>
  </div>
</template>

<style scoped>
.player-editor-shell {
  container-type: inline-size;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.player-editor {
  display: grid;
  gap: var(--editor-space-3);
  min-width: 0;
  color: var(--editor-color-text);
}
.player-editor--items {
  min-height: 0;
}
@container (min-width: 50.001rem) {
  .player-editor--items {
    grid-template-rows: auto auto minmax(0, 1fr);
    height: 100%;
  }
}

.player-character { display: grid; gap: var(--editor-space-3); min-width: 0; }
.player-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .35rem;
  padding: .4rem;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  box-shadow: var(--editor-glass-shadow);
  backdrop-filter: var(--editor-glass-filter);
}
.player-tabs button {
  padding: .75rem 1rem;
  border: 0;
  border-radius: calc(var(--editor-radius-md) - .3rem);
  color: var(--editor-color-muted);
  background: transparent;
  cursor: pointer;
}
.player-tabs button.active { color: var(--editor-color-text); background: var(--editor-color-primary); }

.player-summary,
.player-panel {
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-glass-shadow);
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
  grid-template-columns: minmax(18rem, .75fr) minmax(28rem, 1.25fr);
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
.status-grid,
.effigy-grid { display: grid; gap: var(--editor-space-2); }
.status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.effigy-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.status-panel__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--editor-space-2); }
.status-panel__header h2 { flex: 1; }
.status-legend { display: flex; flex-wrap: wrap; gap: var(--editor-space-2); color: var(--editor-color-muted); font-size: .7rem; }
.status-legend span::before { display: inline-block; width: .65rem; height: .65rem; margin-right: .3rem; border-radius: 50%; content: ''; }
.status-legend__stat::before { background: var(--editor-slider-primary); }
.status-legend__item::before { background: var(--editor-slider-item); }
.status-allocation { white-space: nowrap; }
.status-allocation__stat { color: var(--editor-slider-primary); }
.status-allocation__item { color: var(--editor-slider-item); }
.status-control {
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-control);
}
.status-control header,
.status-control footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-2);
}
.status-control header .status-name { flex: 1; overflow: hidden; }
.status-control footer { color: var(--editor-color-muted); font-size: .7rem; }
.status-name { display: flex; min-width: 0; align-items: center; gap: var(--editor-space-1); }
.status-name img { width: 1.35rem; height: 1.35rem; object-fit: contain; }
.status-control .segmented-range { margin: var(--editor-space-2) 0; }
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

.player-control .number-stepper {
  width: 100%;
  min-width: 0;
  height: 2.35rem;
  flex: 1 1 auto;
  border-radius: var(--editor-radius-sm);
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
  grid-template-columns: 4rem minmax(7.5rem, 1fr) max-content;
  align-items: stretch;
  gap: var(--editor-space-2);
  min-height: 7.5rem;
}
.technology-level__track {
  position: relative;
  display: grid;
  place-items: center;
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
  .effigy-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@container (max-width: 32rem) {
  .status-grid,
  .effigy-grid { grid-template-columns: 1fr; }
  .player-summary,
  .technology-panel__header { align-items: flex-start; }
  .technology-panel__header { flex-direction: column; }
  .technology-level { grid-template-columns: 3.5rem minmax(0, 1fr); }
}
</style>
