<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

</script>

<template>
  <div>
    <button v-if="palStore.HAS_WORKING_PAL_FLAG" @click="palStore.selectPlayer" :disabled="palStore.BASE_PAL_BTN_CLK_FLAG || palStore.LOADING_FLAG" :value="palStore.PAL_BASE_WORKER_BTN">
      Base Pals
    </button>
    <button class="player" v-for="player in palStore.PLAYER_MAP.values()" :value="player.id" @click="palStore.selectPlayer"
      :disabled="player.id == palStore.SELECTED_PLAYER_ID || palStore.LOADING_FLAG">
      {{ player.name }}
    </button>
  </div>
</template>

<style scoped>
div {
    overflow-y:scroll;
    height: 96vh;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    margin-right: 1rem;
}

button {
  margin-bottom: .5rem;
  max-width: 20vw;
  max-height: 5rem;
  padding: .5rem 1rem;
  background-color: #ce9716;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  font-size: 1.2rem;
  transition: all 0.3s ease-in-out;
}

button:hover {
  background-color: #9b7210;
  transition: all 0.3s ease-in-out;
}

button.player {
  background-color: #3365da;
}

button.player:hover {
  background-color: #1b49b4;
}

button:disabled {
  background-color: #8a8a8a;
}

button:disabled:hover {
  background-color: #8a8a8a;
}
</style>
