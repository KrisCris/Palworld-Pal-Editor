<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { watch, ref } from 'vue';
const palStore = usePalEditorStore()

const loadingWidth = ref(0);
const showLoading = ref(false)
const interval = ref(null)

watch(() => palStore.LOADING_FLAG, (newValue) => {
  if (newValue) {
    interval.value = setInterval(() => {
      if (palStore.LOADING_FLAG) {
        if (loadingWidth.value < 20) loadingWidth.value += Math.random() * 8;
        if (loadingWidth.value < 50) loadingWidth.value += Math.random() * 4;
        if (loadingWidth.value < 75) loadingWidth.value += Math.random() * 2;
        if (loadingWidth.value < 98) loadingWidth.value += Math.random() * 1;
      }
    }, 2000);
    showLoading.value = true
    loadingWidth.value = 2
  }

  if (!newValue) {
    loadingWidth.value = 100;
    setTimeout(() => {
      showLoading.value = false
      clearInterval(interval.value);
    }, 250);
  }
});

const donate = async () => {
  if (await palStore.showDonate()) {
    alert(palStore.getTranslatedText("TopBar_Btn_Invalid_Options_ADs"));
    palStore.SHOW_DONATE_FLAG = true;
  }
}

const show_cheats = async () => {
  await donate();
  palStore.HIDE_INVALID_OPTIONS = !palStore.HIDE_INVALID_OPTIONS;
}

const save = async () => {
  if (await palStore.writeSave()) {
    await donate();
  }
}
</script>

<template>
  <div class="loading-bar" v-if="showLoading" :style="{ width: loadingWidth + '%' }"></div>
  <div id="topbar">
    <div class="options" v-if="palStore.SAVE_LOADED_FLAG">
      <p>💾</p>
      <input class="savePath" type="text" v-model="palStore.PAL_WRITE_BACK_PATH"
        :placeholder="palStore.PAL_GAME_SAVE_PATH" :disabled="palStore.LOADING_FLAG">
      <button class="op save" @click="save" :disabled="palStore.LOADING_FLAG">
        💾 {{ palStore.getTranslatedText("TopBar_Btn_Save") }}
      </button>
      <button class="op" @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG">
        🔄 {{ palStore.getTranslatedText("TopBar_Btn_Reload") }}
      </button>
      <button class="op" @click="palStore.reset" :disabled="palStore.LOADING_FLAG">
        🏠 {{ palStore.getTranslatedText("TopBar_Btn_Main_Page") }}
      </button>

      <div class="tooltip-container">
        <button class="op" @click="palStore.updatePal" name="heal_all_pals" :disabled="palStore.LOADING_FLAG">
          💉 {{ palStore.getTranslatedText("TopBar_Btn_HealAllPals") }}
        </button>
        <span class="tooltip-text">{{ palStore.getTranslatedText('TopBar_Btn_HealAllPals_Tooltips') }}</span>
      </div>

      <div class="tooltip-container">
        <button :class="['op', { 'toggled': palStore.SHOW_OOB_PAL_FLAG }]"
          @click="palStore.SHOW_OOB_PAL_FLAG = !palStore.SHOW_OOB_PAL_FLAG" :disabled="palStore.LOADING_FLAG"
          :title="palStore.getTranslatedText('TopBar_Pal_OOB_Tooltips')">
          🧊 {{ palStore.getTranslatedText("TopBar_Btn_Pal_OOB") }}
        </button>
        <span class="tooltip-text">{{ palStore.getTranslatedText('TopBar_Pal_OOB_Tooltips') }}</span>
      </div>

      <div class="tooltip-container">
        <button :class="['op', { 'toggled': palStore.SHOW_UNREF_PAL_FLAG }]"
          @click="palStore.SHOW_UNREF_PAL_FLAG = !palStore.SHOW_UNREF_PAL_FLAG" :disabled="palStore.LOADING_FLAG"
          :title="palStore.getTranslatedText('TopBar_Pal_Ghost_Tooltips')">
          👀 {{ palStore.getTranslatedText("TopBar_Btn_Pal_Ghost") }}
        </button>
        <span class="tooltip-text">{{ palStore.getTranslatedText('TopBar_Pal_Ghost_Tooltips') }}</span>
      </div>

      <div class="tooltip-container">
        <button :class="['op', { 'toggled': palStore.HIDE_INVALID_OPTIONS }]" @click="show_cheats"
          :disabled="palStore.LOADING_FLAG" :title="palStore.getTranslatedText('TopBar_Invalid_Options_Tooltips')">
          ⚠️ {{ palStore.getTranslatedText("TopBar_Btn_Invalid_Options") }}
        </button>
        <span class="tooltip-text">{{ palStore.getTranslatedText('TopBar_Invalid_Options_Tooltips') }}</span>
      </div>

    </div>
    <div class="options">
      <p>🌐</p>
      <select id="languageSelect" v-model="palStore.I18n" @change="palStore.updateI18n"
        :disabled="palStore.LOADING_FLAG">
        <option :value="key" v-for="translated, key in palStore.I18nList">{{ translated }}</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
div#topbar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  z-index: 1000;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

div.loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  background-color: hsla(160, 100%, 37%, 1);
  transition: width 1s ease-out;
}

div.options {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: 0.3rem;
}

select#languageSelect {
  display: flex;
  align-items: center;
  background-color: #272727;
  height: 1.8rem;
  margin: .2rem;
  padding: .2rem .4rem;
  border-radius: .5rem;
  color: rgb(208, 212, 226);
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
}

input.savePath {
  display: flex;
  align-items: center;
  background-color: #34353a;
  height: 1.8rem;
  max-width: 30vw;
  margin: .2rem;
  padding: .2rem .4rem;
  border-radius: .5rem;
  color: rgb(208, 212, 226);
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  border: none;
  outline: none;
}

input.savePath:focus {
  background-color: #b4b7be;
  color: rgb(0, 0, 0);
}

button.op {
  height: 2rem;
  background-color: #414141;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  transition: all 0.15s ease-in-out;
}

button.op:hover {
  background-color: #2c2c2c;
  transition: all 0.15s ease-in-out;
  cursor: pointer;
}

button.op:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button.op.save {
  background-color: #bd1c3c;
}

button.op.save:hover {
  background-color: #830e25;
}

button.op.save:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button.op.toggled {
  background-color: #1cbd64;
}

button.op.toggled:hover {
  background-color: #138d4a;
}

button.op.toggled:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

.tooltip-container {
  position: relative;
  display: inline-block;
}

.tooltip-text {
  visibility: hidden;
  width: 200px;
  background-color: rgba(0, 0, 0, 0.85);
  color: white;
  text-align: center;
  border-radius: 6px;
  padding: 1rem;

  /* Position the tooltip */
  position: absolute;
  z-index: 1;
  top: 100%;
  left: 50%;
  margin-left: -60px;
}

.tooltip-container:hover .tooltip-text {
  visibility: visible;
}
</style>
