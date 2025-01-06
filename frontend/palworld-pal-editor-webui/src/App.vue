<script setup>
import EntryView from './views/EntryView.vue';
import { usePalEditorStore } from '@/stores/paleditor'
import EditorView from './views/EditorView.vue';
import TopBar from './components/TopBar.vue'
import MarkdownModal from "@/components/MarkdownModal.vue";
import AuthView from './views/AuthView.vue';

import { watch, ref, onMounted } from 'vue';
const palStore = usePalEditorStore()

const loadingWidth = ref(0); // Start with 0% width

onMounted(async () => {
  await palStore.fetch_config()
  if (!palStore.HAS_PASSWORD) {
    await palStore.login({ target: { value: "" } })
  }
  await palStore.auth()
})

// Simulate loading progress
const interval = setInterval(() => {
  // Only proceed if loading is true and width is less than 90% to leave room for "completion"
  if (palStore.LOADING_FLAG && loadingWidth.value < 90) {
    loadingWidth.value += Math.random() * 10; // Increase width by a random value
  }
}, 500); // Adjust timing as needed

watch(palStore.LOADING_FLAG, (newValue) => {
  if (!newValue) {
    loadingWidth.value = 100; // Complete the progress
    setTimeout(() => {
      loading.value = false; // Hide the loading bar
      clearInterval(interval); // Stop the interval
    }, 500); // Short delay to show completion
  }
});

</script>

<template>
  <TopBar></TopBar>
  <AuthView v-if="palStore.IS_LOCKED"></AuthView>
  <div v-else>
    <EntryView v-if="!palStore.SAVE_LOADED_FLAG"></EntryView>
    <EditorView v-else></EditorView>
    <MarkdownModal url="/docs/keep_this_project_alive.md">
    </MarkdownModal>
  </div>
</template>

<style>
body {
  display: flex;
  align-items: center;
}

div.loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  /* Several pixels thick */
  background-color: hsla(160, 100%, 37%, 1);
  transition: width 1s ease-out;
}

div.SaveDiv {
  display: flex;
  align-items: center;
  justify-content: center;
  position: fixed;
  /* Fix the position relative to the viewport */
  top: 0;
  /* Pin to the top of the viewport */
  left: 0.3rem;
  /* Pin to the right of the viewport */
  padding: 0.3rem;
  /* Add some padding around the select box */
  z-index: 1000;
  /* Ensure it sits above other content */
}

div.language-selector {
  display: flex;
  align-items: center;
  justify-content: center;
  position: fixed;
  /* Fix the position relative to the viewport */
  top: 0;
  /* Pin to the top of the viewport */
  right: 0.3rem;
  /* Pin to the right of the viewport */
  padding: 0.3rem;
  /* Add some padding around the select box */
  z-index: 1000;
  /* Ensure it sits above other content */
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

button#SAVE_BTN {
  height: 2rem;
  background-color: #bd1c3c;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  /* font-size: 1.2rem; */
  transition: all 0.15s ease-in-out;
}

button#SAVE_BTN:hover {
  background-color: #830e25;
  transition: all 0.15s ease-in-out;
  cursor: pointer;
}

button#SAVE_BTN:disabled {
  background-color: #8a8a8a;
}
</style>
