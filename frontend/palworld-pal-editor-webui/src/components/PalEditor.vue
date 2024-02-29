<script setup>
import PalList from '@/components/PalList.vue';
import PlayerList from '@/components/PlayerList.vue';
import {usePalEditorStore} from '@/stores/paleditor'

const palStore = usePalEditorStore()


</script>

<template>
<div class="grid">
    <div>
        <img class="palIcon" :src="`/image/pals/${palStore.SELECTED_PAL_DATA.IconAccessKey}`" alt="">
        <p>Pal Instance ID: {{ palStore.SELECTED_PAL_ID }}</p>
        <div>
            <input type="text" name="NickName" id="NickName" v-model="palStore.SELECTED_PAL_DATA.NickName" placeholder="NickName" @input="palStore.updatePal">
            <button>X</button>
        </div>
    </div>
</div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(25vh, 1fr));
  /* This is better for small screens, once min() is better supported */
  /* grid-template-columns: repeat(auto-fill, minmax(min(200px, 100%), 1fr)); */
  gap: 1rem;
  max-height: 96vh;
  padding-right: 2rem;
  overflow-y: auto;
}

.grid > div {
  background: #484848;
  padding: 1.5rem;
  border-radius: 1rem;
}

img.palIcon {
    max-width: 20vh;
    border-radius: 50%;
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
}
</style>