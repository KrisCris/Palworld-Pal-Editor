<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

</script>

<template>
  <div class="flex">
    <div class="overflow-container" v-if="palStore.HAS_WORKING_PAL_FLAG">
      <button @click="palStore.selectPlayer" :disabled="palStore.BASE_PAL_BTN_CLK_FLAG || palStore.LOADING_FLAG"
        :value="palStore.PAL_BASE_WORKER_BTN">
        BASE PAL
      </button>
    </div>
    <div class="overflow-container" v-for="player in palStore.PLAYER_MAP.values()">
      <button class="player" :value="player.id" @click="palStore.selectPlayer"
        :disabled="player.id == palStore.SELECTED_PLAYER_ID || palStore.LOADING_FLAG">
        {{ player.name }}
      </button>
    </div>

  </div>
</template>

<style scoped>
div.flex {
  padding-top: .5rem;
  overflow-y: scroll;
  height: calc(100vh - 4rem);
  min-width: 10rem;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding-right: 0.3rem;
  margin-right: .7rem;
}

div.overflow-container {
  display: flex;
  align-items: center;
  width: 10rem;
  /* Fixed width smaller than the button's content */
  overflow-x: auto;
  /* Enable horizontal scrolling */
  white-space: nowrap;
  /* Prevent content from wrapping */
  min-height: 3rem;
}

button {
  min-width: 100%;
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
