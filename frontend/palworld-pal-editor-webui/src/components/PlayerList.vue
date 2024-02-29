<script setup>
import {usePalEditorStore} from '@/stores/paleditor'
const palStore = usePalEditorStore()

</script>

<template>
<button v-for="player in palStore.playerMap.values()" :value="player.id" @click="palStore.selectPlayer">
  {{ player.name }}
</button>
</template>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  position: relative;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

h1,
h3 {
  text-align: center;
}

@media (min-width: 1024px) {
  h1,
  h3 {
    text-align: left;
  }
}

button{
    margin-bottom: 1rem;
    width: 100%;
    height: 3rem;
    background-color: #3365da;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease-in-out;
}

button:hover{
    background-color: #1b49b4;
    transition: all 0.3s ease-in-out;
}
</style>
