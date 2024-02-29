<script setup>
import {usePalEditorStore} from '@/stores/paleditor'
const palStore = usePalEditorStore()

</script>

<template>
<h1 v-if="palStore.LOADING_FLAG">NOW LOADING...</h1>
</template>

<style scoped>

</style>