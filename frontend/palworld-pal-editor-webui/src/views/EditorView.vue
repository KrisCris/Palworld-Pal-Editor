<script setup>
import PalList from '@/components/PalList.vue';
import PlayerList from '@/components/PlayerList.vue';
import {usePalEditorStore} from '@/stores/paleditor'

const palStore = usePalEditorStore()


</script>

<template>
<PlayerList></PlayerList>
<PalList v-if="palStore"></PalList>
</template>
