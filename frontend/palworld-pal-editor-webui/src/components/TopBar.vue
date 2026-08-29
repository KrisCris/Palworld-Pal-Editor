<script setup>
import { computed, ref, watch } from 'vue'

import BackendServerSelector from './BackendServerSelector.vue'
import PalList from './PalList.vue'
import PlayerList from './PlayerList.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'
import { usePalsStore } from '@/stores/pals'
import { usePlayersStore } from '@/stores/players'
import { useRostersStore } from '@/stores/rosters'
import { useSessionStore } from '@/stores/session'

const palStore = usePalEditorStore()
const palsStore = usePalsStore()
const playersStore = usePlayersStore()
const rostersStore = useRostersStore()
const sessionStore = useSessionStore()
defineProps({ playersCollapsed: Boolean, palsCollapsed: Boolean })
const emit = defineEmits(['restorePlayers', 'restorePals'])
const loadingWidth = ref(0)
const showLoading = ref(false)
const interval = ref(null)

watch(() => sessionStore.operationPending, newValue => {
  if (newValue) {
    interval.value = setInterval(() => {
      if (loadingWidth.value < 20) loadingWidth.value += Math.random() * 8
      if (loadingWidth.value < 50) loadingWidth.value += Math.random() * 4
      if (loadingWidth.value < 75) loadingWidth.value += Math.random() * 2
      if (loadingWidth.value < 98) loadingWidth.value += Math.random()
    }, 2000)
    showLoading.value = true
    loadingWidth.value = 2
    return
  }
  loadingWidth.value = 100
  setTimeout(() => {
    showLoading.value = false
    clearInterval(interval.value)
  }, 250)
})

const donate = async () => {
  if (await palStore.showDonate()) palStore.SHOW_DONATE_FLAG = true
}

const show_cheats = async () => {
  await donate()
  palStore.HIDE_INVALID_OPTIONS = !palStore.HIDE_INVALID_OPTIONS
}

const save = async () => {
  if (await palStore.writeSave()) await donate()
}

const playerCount = computed(() => playersStore.players.length + (palStore.HAS_WORKING_PAL_FLAG ? 1 : 0))
const palCount = computed(() => rostersStore.activeRecordKeys.length)
const hasPalRoster = computed(() => rostersStore.activeRosterKey)
// A pal requires "heal" exactly like the per-pal action in PalEditor: HasWorkerSick.
const hasPalToHeal = computed(() => palsStore.hasSickPal)
</script>

<template>
  <header id="topbar" class="editor-toolbar">
    <div v-if="showLoading" class="loading-bar" :style="{ width: loadingWidth + '%' }"></div>
    <div class="editor-app-bar">
      <div class="editor-app-bar__primary">
        <template v-if="sessionStore.editorOpen">
          <UiIcon name="save" />
          <input class="savePath" type="text" :value="sessionStore.writeBackPath || sessionStore.savePath"
            :title="sessionStore.writeBackPath || sessionStore.savePath" readonly>
          <button class="op op--primary" @click="save"
            :title="palStore.getTranslatedText('TopBar_Btn_Save')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Save')">
            <UiIcon name="save" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Save") }}</span>
          </button>
          <button class="op" @click="palStore.loadSave"
            :title="palStore.getTranslatedText('TopBar_Btn_Reload')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Reload')">
            <UiIcon name="refresh" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Reload") }}</span>
          </button>
          <button class="op" @click="palStore.reset"
            :title="palStore.getTranslatedText('TopBar_Btn_Main_Page')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Main_Page')">
            <UiIcon name="home" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Main_Page") }}</span>
          </button>
        </template>
        <div v-else class="entry-brand">
          <img src="@/assets/logo.ico" alt="">
          <span>
            <strong>Palworld Pal Editor</strong>
            <small>Developed by _connlost</small>
          </span>
        </div>
      </div>

      <div v-if="sessionStore.editorOpen" class="editor-app-bar__tools">
        <button v-if="hasPalToHeal" class="op op--primary" @click="palStore.updatePal" name="heal_all_pals"
          :title="palStore.getTranslatedText('TopBar_Btn_HealAllPals_Tooltips')">
          <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/heal')" alt="">
          {{ palStore.getTranslatedText("TopBar_Btn_HealAllPals") }}
        </button>
        <button :class="['op', { toggled: !palStore.HIDE_INVALID_OPTIONS }]" @click="show_cheats"
          :aria-pressed="!palStore.HIDE_INVALID_OPTIONS"
          :title="palStore.getTranslatedText('TopBar_Invalid_Options_Tooltips')">
          <UiIcon name="warning" /> {{ palStore.getTranslatedText("TopBar_Btn_Invalid_Options") }}
        </button>
      </div>

      <div class="editor-app-bar__utilities">
        <button v-if="sessionStore.editorOpen" class="op support-button"
          @click="palStore.SHOW_DONATE_FLAG = !palStore.SHOW_DONATE_FLAG">
          <UiIcon name="heart" /> {{ palStore.getTranslatedText("TopBar_Btn_Donation") }}
        </button>
        <BackendServerSelector v-if="sessionStore.appState !== 'editor'" />
        <label class="language-control">
          <UiIcon name="language" />
          <select id="languageSelect" v-model="palStore.I18n" @change="palStore.updateI18n"
            :aria-label="palStore.getTranslatedText('TopBar_Language_Label')">
            <option :value="key" v-for="translated, key in palStore.I18nList" :key="key">{{ translated }}</option>
          </select>
        </label>
      </div>

      <div v-if="sessionStore.editorOpen && (playersCollapsed || (palsCollapsed && hasPalRoster))" class="editor-app-bar__roster">
        <div v-if="playersCollapsed" class="editor-roster-dock">
          <button class="editor-roster-pill" :title="palStore.getTranslatedText('PlayerList_Restore')"
            :aria-label="palStore.getTranslatedText('PlayerList_Restore')">
            <UiIcon name="paw" /> <span>{{ palStore.getTranslatedText('PlayerList_Text') }}</span>
            <small>{{ playerCount }}</small>
          </button>
          <aside class="editor-roster-preview editor-roster-preview--players">
            <PlayerList preview @toggle="emit('restorePlayers')" />
          </aside>
        </div>
        <div v-if="palsCollapsed && hasPalRoster" class="editor-roster-dock">
          <button class="editor-roster-pill" :title="palStore.getTranslatedText('PalList_Restore')"
            :aria-label="palStore.getTranslatedText('PalList_Restore')">
            <UiIcon name="paw" /> <span>{{ palStore.getTranslatedText('PalList_Text') }}</span>
            <small>{{ palCount }}</small>
          </button>
          <aside class="editor-roster-preview editor-roster-preview--pals">
            <PalList preview @toggle="emit('restorePals')" />
          </aside>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.editor-toolbar {
  position: relative;
  z-index: 20;
  display: grid;
  border-bottom: 1px solid var(--editor-color-glass-border);
  box-shadow: var(--editor-glass-shadow);
}

.editor-toolbar::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  content: '';
  background: var(--editor-color-glass-toolbar);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
}

.loading-bar {
  position: absolute;
  z-index: 1;
  top: 0;
  left: 0;
  height: 2px;
  background: var(--editor-color-success);
  transition: width 1s ease-out;
}

.editor-app-bar__roster,
.editor-app-bar__primary,
.editor-app-bar__tools,
.editor-app-bar__utilities,
.language-control {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--editor-space-2);
}

.editor-app-bar {
  display: grid;
  grid-template-columns: 1fr auto auto;
  grid-template-areas:
    "primary tools utilities"
    "roster roster roster";
  column-gap: var(--editor-space-2);
  align-items: center;
  padding: var(--editor-space-2) var(--editor-space-3);
}

.editor-app-bar__primary {
  grid-area: primary;
  min-width: 0;
}

.entry-brand {
  display: flex;
  align-items: center;
  gap: var(--editor-space-2);
}

.entry-brand img {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
}

.entry-brand strong,
.entry-brand small {
  display: block;
}

.entry-brand small {
  color: var(--editor-color-muted);
}

.editor-app-bar__tools {
  grid-area: tools;
  min-width: 0;
}

.editor-app-bar__utilities {
  grid-area: utilities;
}

.editor-app-bar__roster {
  grid-area: roster;
  position: relative;
  flex-wrap: wrap;
  /* Space between the main line and the capsule line; only present
     when this row actually renders, so a single-line bar stays flush. */
  margin-top: var(--editor-space-2);
}

.editor-roster-dock {
  position: relative;
  flex: 0 0 auto;
  animation: roster-dock-in .2s ease-out;
}

.editor-roster-dock::after {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  height: var(--editor-space-2);
  content: '';
}

.editor-roster-pill {
  display: inline-flex;
  min-height: 2.25rem;
  align-items: center;
  gap: .35rem;
  padding: 0 var(--editor-space-3);
  border: 1px solid var(--editor-color-glass-border);
  border-radius: 999px;
  color: var(--editor-color-text);
  background: var(--editor-color-glass-surface);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-shadow-compact);
  cursor: pointer;
}

.editor-roster-pill:hover {
  border-color: var(--editor-color-glass-border);
  background: var(--editor-color-glass-surface);
  box-shadow: var(--editor-glass-shadow);
}

.editor-roster-pill small {
  color: var(--editor-color-muted);
  font-variant-numeric: tabular-nums;
}

.editor-roster-preview {
  position: absolute;
  z-index: 30;
  top: calc(100% + var(--editor-space-2));
  left: 0;
  visibility: hidden;
  opacity: 0;
  height: min(34rem, calc(100dvh - 9rem));
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-glass-shadow);
  transition: opacity .12s ease .14s, visibility 0s linear .26s;
}

.editor-roster-preview--players { width: 11rem; }
.editor-roster-preview--pals { width: 17rem; }

.editor-roster-dock:hover .editor-roster-preview,
.editor-roster-dock:focus-within .editor-roster-preview,
.editor-roster-preview:hover {
  visibility: visible;
  opacity: 1;
  transition-delay: 0s;
  animation: roster-preview-enter .16s ease-out;
}

.editor-roster-pill:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@keyframes roster-dock-in {
  from { opacity: .5; transform: translate(-1rem, 1rem) scale(.82); }
  to { opacity: 1; transform: none; }
}

@keyframes roster-preview-enter {
  from { opacity: 0; transform: translateY(-.5rem); }
  to { opacity: 1; transform: none; }
}

.op,
#languageSelect,
.savePath {
  min-height: 2.25rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.op {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .35rem;
  flex: 0 0 auto;
  padding: 0 var(--editor-space-3);
  white-space: nowrap;
  cursor: pointer;
}

.op--primary {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.op:hover {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
}

.op:hover .ui-icon {
  color: var(--editor-color-primary);
}

.op--primary:hover {
  color: var(--editor-color-background);
  background: var(--editor-color-primary-hover);
}

.op--primary:hover .ui-icon {
  color: currentcolor;
}

.op.toggled {
  border-color: var(--editor-color-success);
  color: var(--editor-color-success);
  background: color-mix(in srgb, var(--editor-color-success) 18%, var(--editor-color-surface-raised));
}

.op:disabled,
.op:disabled:hover,
#languageSelect:disabled,
.savePath:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
  cursor: not-allowed;
}

.op:focus-visible,
#languageSelect:focus-visible,
.savePath:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

.savePath {
  flex: 0 1 auto;
  width: min(26rem, 38vw);
  min-width: 8rem;
  padding: 0 var(--editor-space-3);
  text-align: right;
  cursor: text;
}

.support-button {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-primary);
  background: color-mix(in srgb, var(--editor-color-primary) 12%, var(--editor-color-control));
}

#languageSelect {
  padding: 0 var(--editor-space-2);
}

.game-icon {
  width: 1.1rem;
  height: 1.1rem;
  object-fit: contain;
}

@media (max-width: 1180px) {
  /* Keep the Donate + language switcher on the first line; drop the other
     tool buttons (heal / cheats) onto the second line next to the capsules.
     Both right-side groups stay flush right. */
  .editor-app-bar {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      "primary utilities"
      "roster tools";
  }

  .editor-app-bar__utilities,
  .editor-app-bar__tools {
    justify-content: flex-end;
  }

  .editor-app-bar__tools {
    margin-top: var(--editor-space-2);
  }
}

@media (max-width: 760px) {
  /* Stay on two rows (matching the layout above) and just compact the
     controls so everything still fits on narrow windows. */
  .op span {
    display: none;
  }

  .savePath {
    width: min(16rem, 34vw);
    min-width: 7rem;
  }

  .editor-roster-preview--pals { 
    left: auto;
    right: 0px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .editor-roster-dock,
  .editor-roster-dock:hover .editor-roster-preview,
  .editor-roster-dock:focus-within .editor-roster-preview,
  .editor-roster-preview:hover { animation: none; }
}
</style>
