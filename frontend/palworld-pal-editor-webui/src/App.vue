<script setup>
import EntryView from './views/EntryView.vue';
import {usePalEditorStore} from '@/stores/paleditor'
import EditorView from './views/EditorView.vue';
import LoadingIndicator from './components/ LoadingIndicator.vue';
const palStore = usePalEditorStore()


</script>

<template>
    <!-- <LoadingIndicator></LoadingIndicator> -->
    <div id="mainContainer">
      <EntryView v-if="!palStore.SAVE_LOADED_FLAG"></EntryView>
      <EditorView v-else></EditorView>
    </div>
</template>

<style>

#app {
  margin: 0 0;
  padding: 2vh;
  padding-right: 0;
  font-weight: normal;
  display: flex;
  align-items:flex-start
}

button:disabled {
  background-color: #8a8a8a;
}

button:disabled:hover {
  background-color: #8a8a8a;
}

div#mainContainer {
  display: flex;
  flex-direction: column;
  align-items:flex-start
}
</style>
