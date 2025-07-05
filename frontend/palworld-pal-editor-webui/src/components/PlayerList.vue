<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { ref, computed, reactive, onMounted, nextTick } from "vue";
const palStore = usePalEditorStore()
const playerListContainer = ref(null);
onMounted(async () => {
  await nextTick(); // Wait for the DOM to update with the dynamic buttons
  const buttons = playerListContainer.value.querySelectorAll('button:not(:disabled)');
  if (buttons.length > 0) {
    buttons[0].click(); // Simulate a click on the first enabled button
  }
});
</script>

<template>
  <div class="flex">
    <div class="title">
      <p>
        {{ palStore.getTranslatedText("PlayerList_Text") }}
      </p>
      <div class="tooltip-container">
        <button class="playerSettings"
          v-if="palStore.SELECTED_PLAYER_ID != null && !palStore.PLAYER_MAP.get(palStore.SELECTED_PLAYER_ID).HasViewingCage"
          :title="palStore.getTranslatedText('PlayerList_Viewing_Cage')" :disabled="palStore.LOADING_FLAG"
          @click="palStore.updatePlayer" name="unlock_viewing_cage">🧊</button>
        <span class="tooltip-text">{{ palStore.getTranslatedText('PlayerList_Viewing_Cage') }}</span>
      </div>
    </div>
    <div class="overflow-list" ref="playerListContainer">
      <div class="overflow-container" v-if="palStore.HAS_WORKING_PAL_FLAG">
        <button class="player" @click="palStore.selectPlayer(palStore.PAL_BASE_WORKER_BTN)"
          :disabled="palStore.BASE_PAL_BTN_CLK_FLAG || palStore.LOADING_FLAG">
          {{ palStore.getTranslatedText('PlayerList_Base_Pal') }}
        </button>
      </div>
      <div class="overflow-container" v-for="player in palStore.PLAYER_MAP.values()">
        <button class="player real" @click="palStore.selectPlayer(player.InstanceId)" :title="player.InstanceId"
          :disabled="(player.InstanceId == palStore.SELECTED_PLAYER_ID && palStore.SHOW_PLAYER_EDIT_FLAG) || palStore.LOADING_FLAG"
          :selected="player.InstanceId == palStore.SELECTED_PLAYER_ID">
          {{ player.NickName }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
div.flex {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: var(--sub-height);
  width: 10rem;
  padding-right: 0.3rem;
  /* scrollbar */
}

div.title {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: .5rem;
}

div.overflow-list {
  display: flex;
  flex-direction: column;
  overflow-y: scroll;
  gap: .2rem 0rem;
}

div.overflow-container {
  align-items: center;
  display: flex;
  overflow-x: auto;
  white-space: nowrap;
  max-height: 3.5rem;
  flex-shrink: 0;
  padding-bottom: 0.1rem;
  /* scrollbar */
}

button.player {
  min-width: 100%;
  max-height: 5rem;
  padding: .5rem 1rem;
  background-color: #ce9716;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  font-size: 1.2rem;
  transition: all 0.15s ease-in-out;
  cursor: pointer;
}

button.playerSettings {
  background-color: rgb(54, 54, 54);
  padding: 0;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.2rem;
  font-size: 1rem;
}

button.playerSettings:hover {
  background-color: rgb(123, 123, 123);
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  cursor: pointer;
}

button.player:hover {
  background-color: #9b7210;
  transition: all 0.15s ease-in-out;
}

button.player.real {
  background-color: #3365da;
}

button.player.real:hover {
  background-color: #1b49b4;
}

button.player.real:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button.player:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button.playerSettings:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button.player[selected="true"] {
  box-shadow: 0 0 0;
  filter: grayscale(60%);
  border-color: #1cff4d;
  border-style: solid;
  border-width: 0.15rem;
}

.tooltip-text {
  visibility: hidden;
  width: 200px;
  background-color: rgba(0, 0, 0, 0.85);
  color: white;
  text-align: center;
  border-radius: 6px;
  padding: 1rem;

  position: absolute;
  z-index: 1;
  top: 5rem;
  margin-left: -60px;
}

.tooltip-container:hover .tooltip-text {
  visibility: visible;
}
</style>
