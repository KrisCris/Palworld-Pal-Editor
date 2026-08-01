<script setup>
import { ref, watch } from 'vue'

import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
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
</script>

<template>
  <header id="topbar" class="editor-toolbar">
    <div v-if="showLoading" class="loading-bar" :style="{ width: loadingWidth + '%' }"></div>
    <div class="editor-app-bar">
      <div class="editor-app-bar__primary">
        <template v-if="palStore.SAVE_LOADED_FLAG">
          <UiIcon name="save" />
          <input class="savePath" type="text" v-model="palStore.PAL_WRITE_BACK_PATH"
            :placeholder="palStore.PAL_GAME_SAVE_PATH" :disabled="palStore.LOADING_FLAG">
          <button class="op save" @click="save" :disabled="palStore.LOADING_FLAG"
            :title="palStore.getTranslatedText('TopBar_Btn_Save')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Save')">
            <UiIcon name="save" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Save") }}</span>
          </button>
          <button class="op" @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG"
            :title="palStore.getTranslatedText('TopBar_Btn_Reload')"
            :aria-label="palStore.getTranslatedText('TopBar_Btn_Reload')">
            <UiIcon name="refresh" /> <span>{{ palStore.getTranslatedText("TopBar_Btn_Reload") }}</span>
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
          <div class="editor-more__menu">
            <button class="op" @click="palStore.reset" :disabled="palStore.LOADING_FLAG">
              <UiIcon name="home" /> {{ palStore.getTranslatedText("TopBar_Btn_Main_Page") }}
            </button>
            <button class="op" @click="palStore.SHOW_DONATE_FLAG = !palStore.SHOW_DONATE_FLAG"
              :disabled="palStore.LOADING_FLAG">
              <UiIcon name="heart" /> {{ palStore.getTranslatedText("TopBar_Btn_Donation") }}
            </button>
          </div>
        </details>
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
      <button class="op" @click="palStore.updatePal" name="heal_all_pals" :disabled="palStore.LOADING_FLAG"
        :title="palStore.getTranslatedText('TopBar_Btn_HealAllPals_Tooltips')">
        <img class="game-icon" :src="'/image/ui/heal'" alt="">
        {{ palStore.getTranslatedText("TopBar_Btn_HealAllPals") }}
      </button>
      <button :class="['op', { toggled: palStore.SHOW_OOB_PAL_FLAG }]"
        @click="palStore.SHOW_OOB_PAL_FLAG = !palStore.SHOW_OOB_PAL_FLAG"
        :aria-pressed="palStore.SHOW_OOB_PAL_FLAG" :disabled="palStore.LOADING_FLAG"
        :title="palStore.getTranslatedText('TopBar_Pal_OOB_Tooltips')">
        <UiIcon name="eye" /> {{ palStore.getTranslatedText("TopBar_Btn_Pal_OOB") }}
      </button>
      <button :class="['op', { toggled: !palStore.HIDE_INVALID_OPTIONS }]" @click="show_cheats"
        :aria-pressed="!palStore.HIDE_INVALID_OPTIONS" :disabled="palStore.LOADING_FLAG"
        :title="palStore.getTranslatedText('TopBar_Invalid_Options_Tooltips')">
        <UiIcon name="warning" /> {{ palStore.getTranslatedText("TopBar_Btn_Invalid_Options") }}
      </button>
    </div>
  </header>
</template>

<style scoped>
.editor-toolbar {
  position: relative;
  z-index: 20;
  display: grid;
  border-bottom: 1px solid var(--editor-color-glass-border);
  background: var(--editor-color-glass-toolbar);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-glass-shadow);
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
  flex-wrap: wrap;
  padding: 0 var(--editor-space-3) var(--editor-space-2);
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

.editor-app-bar__primary .op,
.editor-context-bar .op {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.op:hover {
  color: var(--editor-color-background);
  background: var(--editor-color-primary-hover);
}

.op.toggled {
  border-color: var(--editor-color-success);
  color: var(--editor-color-success);
  background: color-mix(in srgb, var(--editor-color-success) 18%, var(--editor-color-surface-raised));
}

.op.save {
  border-color: var(--editor-color-danger);
  color: var(--editor-color-text);
  background: color-mix(in srgb, var(--editor-color-danger) 18%, var(--editor-color-surface-raised));
}

.op.save:hover {
  color: var(--editor-color-text);
  background: color-mix(in srgb, var(--editor-color-danger) 30%, var(--editor-color-surface-raised));
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
  background: var(--editor-color-surface-raised);
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
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .editor-app-bar__primary {
    width: 100%;
  }

  .savePath {
    flex: 1;
    width: auto;
  }
}

@media (max-width: 480px) {
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
}
</style>
