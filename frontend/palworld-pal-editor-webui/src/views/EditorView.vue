<script setup>
import PalList from '@/components/PalList.vue';
import PlayerList from '@/components/PlayerList.vue';
import PalEditor from '@/components/PalEditor.vue';
import PlayerEditor from '@/components/PlayerEditor.vue';
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()
</script>

<template>
    <div id="EditorDiv">
        <div id="EditorMain">
            <PlayerList></PlayerList>
            <PalList v-if="palStore.SELECTED_PLAYER_ID || palStore.BASE_PAL_BTN_CLK_FLAG"></PalList>
            <PlayerEditor v-if="palStore.SHOW_PLAYER_EDIT_FLAG"></PlayerEditor>
            <PalEditor v-else-if="palStore.SELECTED_PAL_ID && palStore.SELECTED_PAL_DATA"></PalEditor>
            <p v-else>SELECT A PAL OR PLAYER TO START ;）</p>
        </div>
    </div>
</template>
<style scoped>
div#EditorDiv {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    justify-content: center;
    align-items: center;
}

div#EditorMain {
    display: flex;
    flex-direction: row;
    gap: 0rem 1rem;
    width: calc(100vw - 4vh);
    margin-top: var(--editor-top-offset);
}
</style>