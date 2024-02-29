<script setup>
import { RouterView } from 'vue-router'
import EntryView from './views/EntryView.vue';
import {usePalEditorStore} from '@/stores/paleditor'
import EditorView from './views/EditorView.vue';
import LoadingIndicator from './components/ LoadingIndicator.vue';
const palStore = usePalEditorStore()


</script>

<template>
  <LoadingIndicator></LoadingIndicator>
  <EntryView v-if="!palStore.saveLoaded"></EntryView>
  <EditorView v-else></EditorView>
</template>

<style scoped>

</style>
