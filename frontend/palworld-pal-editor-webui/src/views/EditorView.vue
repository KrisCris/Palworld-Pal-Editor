<script setup>
import PalList from '@/components/PalList.vue';
import PlayerList from '@/components/PlayerList.vue';
import PalEditor from '@/components/PalEditor.vue';
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()


</script>

<template>
    <div id="editorDiv">
        <PlayerList></PlayerList>
        <PalList v-if="palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG"></PalList>
        <PalEditor v-if="palStore.SELECTED_PAL_ID && palStore.SELECTED_PAL_DATA"></PalEditor>
    </div>
</template>
<style>
div#editorDiv {
    display: flex;
    flex-direction: row;
    
}
</style>