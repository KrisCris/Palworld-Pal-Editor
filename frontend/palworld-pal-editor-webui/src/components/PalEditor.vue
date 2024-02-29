<script setup>
import PalList from '@/components/PalList.vue';
import PlayerList from '@/components/PlayerList.vue';
import {usePalEditorStore} from '@/stores/paleditor'

const palStore = usePalEditorStore()


</script>

<template>
<div>
    {{ palStore.SELECTED_PAL_ID }}
</div>
</template>