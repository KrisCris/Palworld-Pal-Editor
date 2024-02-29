<script setup>
import EntryView from './views/EntryView.vue';
import {usePalEditorStore} from '@/stores/paleditor'
import EditorView from './views/EditorView.vue';
import LoadingIndicator from './components/ LoadingIndicator.vue';
const palStore = usePalEditorStore()


</script>

<template>
    <!-- <LoadingIndicator></LoadingIndicator> -->
    <EntryView v-if="!palStore.SAVE_LOADED_FLAG"></EntryView>
    <EditorView v-else></EditorView>
</template>

<style>
button:disabled {
  background-color: #8a8a8a;
}

button:disabled:hover {
  background-color: #8a8a8a;
}
</style>
