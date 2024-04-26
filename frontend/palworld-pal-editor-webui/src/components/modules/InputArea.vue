<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

defineProps(['placeholder'])
const model = defineModel()

</script>

<template>
    <input type="text" v-model="model" :placeholder="placeholder" :disabled="palStore.LOADING_FLAG">
</template>

<style scoped>
input {
    display: flex;
    align-items: center;
    background-color: #34353a;
    height: 1.6rem;
    max-width: 100%;
    /* margin: .2rem; */
    padding: .2rem .4rem;
    border-radius: .5rem;
    color: rgb(208, 212, 226);
    /* box-shadow: 2px 2px 10px rgb(38, 38, 38); */
    transition: all 0.15s ease-in-out;

    border: none;
    outline: none;
    flex: 1;
}

input:focus {
    background-color: #b4b7be;
    transition: all 0.15s ease-in-out;

    color: rgb(0, 0, 0);
}
</style>