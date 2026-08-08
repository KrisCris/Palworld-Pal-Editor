<script setup>
import { computed, ref, watch } from 'vue'

import BackendServerSelector from './BackendServerSelector.vue'
import PalList from './PalList.vue'
import PlayerList from './PlayerList.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
defineProps({ playersCollapsed: Boolean, palsCollapsed: Boolean })
const emit = defineEmits(['restorePlayers', 'restorePals'])
const loadingWidth = ref(0)
const showLoading = ref(false)
const interval = ref(null)

watch(() => palStore.LOADING_FLAG, newValue => {
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

const playerCount = computed(() => palStore.PLAYER_MAP.size + (palStore.HAS_WORKING_PAL_FLAG ? 1 : 0))
const palCount = computed(() => palStore.PAL_MAP.size)
const hasPalRoster = computed(() => palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG)
</script>

<template>
  <header id="topbar" class="editor-toolbar">
    <div v-if="showLoading" class="loading-bar" :style="{ width: loadingWidth + '%' }"></div>
    <div class="editor-app-bar">
      <div class="editor-app-bar__primary">
        <template v-if="palStore.SAVE_LOADED_FLAG">
          <UiIcon name="save" />
          <input class="savePath" type="text" :value="palStore.PAL_WRITE_BACK_PATH || palStore.PAL_GAME_SAVE_PATH"
            :title="palStore.PAL_WRITE_BACK_PATH || palStore.PAL_GAME_SAVE_PATH" readonly>
          <button class="op op--primary" @click="save" :disabled="palStore.LOADING_FLAG"
            :title="palStore.getTranslatedText('TopBar_Btn_Save')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Save')">
            <UiIcon name="save" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Save") }}</span>
          </button>
          <button class="op" @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG"
            :title="palStore.getTranslatedText('TopBar_Btn_Reload')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Reload')">
            <UiIcon name="refresh" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Reload") }}</span>
          </button>
          <button class="op" @click="palStore.reset" :disabled="palStore.LOADING_FLAG"
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

      <div class="editor-app-bar__utilities">
        <details v-if="palStore.SAVE_LOADED_FLAG" class="editor-more">
          <summary class="op"><UiIcon name="more" /> {{ palStore.getTranslatedText("TopBar_More") }}</summary>
          <div class="editor-more__menu editor-glass-surface">
            <button :class="['op', { toggled: palStore.SHOW_OOB_PAL_FLAG }]"
              @click="palStore.SHOW_OOB_PAL_FLAG = !palStore.SHOW_OOB_PAL_FLAG"
              :aria-pressed="palStore.SHOW_OOB_PAL_FLAG" :disabled="palStore.LOADING_FLAG"
              :title="palStore.getTranslatedText('TopBar_Pal_OOB_Tooltips')">
              <UiIcon name="eye" /> {{ palStore.getTranslatedText("TopBar_Btn_Pal_OOB") }}
            </button>
          </div>
        </details>
        <button v-if="palStore.SAVE_LOADED_FLAG" class="op support-button"
          @click="palStore.SHOW_DONATE_FLAG = !palStore.SHOW_DONATE_FLAG" :disabled="palStore.LOADING_FLAG">
          <UiIcon name="heart" /> {{ palStore.getTranslatedText("TopBar_Btn_Donation") }}
        </button>
        <BackendServerSelector v-if="palStore.APP_STATE !== 'editor'" />
        <label class="language-control">
          <UiIcon name="language" />
          <select id="languageSelect" v-model="palStore.I18n" @change="palStore.updateI18n"
            :aria-label="palStore.getTranslatedText('TopBar_Language_Label')"
            :disabled="palStore.LOADING_FLAG">
            <option :value="key" v-for="translated, key in palStore.I18nList" :key="key">{{ translated }}</option>
          </select>
        </label>
      </div>
    </div>

    <div v-if="palStore.SAVE_LOADED_FLAG" class="editor-context-bar">
      <div v-if="playersCollapsed" class="editor-roster-dock">
        <button class="editor-roster-pill" :title="palStore.getTranslatedText('PlayerList_Restore')"
          :aria-label="palStore.getTranslatedText('PlayerList_Restore')">
          <UiIcon name="users" /> <span>{{ palStore.getTranslatedText('PlayerList_Text') }}</span>
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
      <div class="editor-context-actions">
        <button class="op op--primary" @click="palStore.updatePal" name="heal_all_pals" :disabled="palStore.LOADING_FLAG"
          :title="palStore.getTranslatedText('TopBar_Btn_HealAllPals_Tooltips')">
          <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/heal')" alt="">
          {{ palStore.getTranslatedText("TopBar_Btn_HealAllPals") }}
        </button>
        <button :class="['op', { toggled: !palStore.HIDE_INVALID_OPTIONS }]" @click="show_cheats"
          :aria-pressed="!palStore.HIDE_INVALID_OPTIONS" :disabled="palStore.LOADING_FLAG"
          :title="palStore.getTranslatedText('TopBar_Invalid_Options_Tooltips')">
          <UiIcon name="warning" /> {{ palStore.getTranslatedText("TopBar_Btn_Invalid_Options") }}
        </button>
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

.editor-app-bar,
.editor-context-bar,
.editor-app-bar__primary,
.editor-app-bar__utilities,
.language-control {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--editor-space-2);
}

.editor-app-bar {
  justify-content: space-between;
  padding: var(--editor-space-2) var(--editor-space-3);
}

.editor-app-bar__primary {
  flex: 1;
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

.editor-app-bar__utilities {
  flex: 0 0 auto;
}

.editor-context-bar {
  position: relative;
  flex-wrap: wrap;
  padding: 0 var(--editor-space-3) var(--editor-space-2);
}

.editor-context-actions {
  display: flex;
  align-items: center;
  gap: var(--editor-space-2);
  margin-left: auto;
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
  padding: 0 var(--editor-space-3);
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

.editor-more {
  position: relative;
}

.editor-more summary {
  list-style: none;
}

.editor-more summary::-webkit-details-marker {
  display: none;
}

.editor-more__menu {
  position: absolute;
  top: calc(100% + var(--editor-space-1));
  right: 0;
  display: grid;
  min-width: 12rem;
  gap: var(--editor-space-1);
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  box-shadow: var(--editor-shadow-compact);
}

.editor-more__menu .op {
  justify-content: flex-start;
}

.game-icon {
  width: 1.1rem;
  height: 1.1rem;
  object-fit: contain;
}

@media (max-width: 760px) {
  .editor-app-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .editor-app-bar__primary,
  .editor-app-bar__utilities {
    grid-column: 1 / -1;
  }

  .editor-app-bar__utilities {
    justify-content: flex-end;
  }

  .op span {
    display: none;
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
