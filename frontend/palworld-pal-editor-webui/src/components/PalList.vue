<script setup>
import {usePalEditorStore} from '@/stores/paleditor'
const palStore = usePalEditorStore()


</script>

<template>
<button v-for="pal in palStore.palMap.values()">
    <img class="palIcon" :src="`/image/pals/${pal.IconAccessKey}`">
    {{ pal.DisplayName }}
</button>
</template>

<style scoped>
img.palIcon {
    width: 30px;
}

</style>