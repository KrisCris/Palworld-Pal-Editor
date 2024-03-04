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
      if (palStore.LOADING_FLAG && loadingWidth.value < 90) {
        loadingWidth.value += Math.random() * 10;
      }
    }, 500);
    showLoading.value = true
    loadingWidth.value = 0
  }

  if (!newValue) {
    loadingWidth.value = 100;
    setTimeout(() => {
      showLoading.value = false
      clearInterval(interval.value);
    }, 250);
  }
});
</script>

<template>
  <div class="loading-bar" v-if="showLoading" :style="{ width: loadingWidth + '%' }"></div>
  <div id="topbar">
    <div class="options" v-if="palStore.SAVE_LOADED_FLAG">
      <p>💾</p>
      <input class="savePath" type="text" v-model="palStore.PAL_WRITE_BACK_PATH"
        :placeholder="palStore.PAL_GAME_SAVE_PATH">
      <button class="op save" @click="palStore.writeSave">💾 SAVE CHANGES</button>
      <button class="op" @click="palStore.loadSave">🔄 Reload Save</button>
      <button class="op" @click="palStore.reset">🏠 Return to Main Page</button>
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

<style>
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
  width: 40vw;
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
}

button.op.save {
  background-color: #bd1c3c;
}

button.op.save:hover {
  background-color: #830e25;
}
</style>
