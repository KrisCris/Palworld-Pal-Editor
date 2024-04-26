<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

defineProps(['icon', 'name', 'value'])
defineEmits([])
</script>

<template>
    <button :name="name" :value="value" :disabled="palStore.LOADING_FLAG">
        {{ icon }}
    </button>
</template>

<style scoped>
button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    padding: 0;
    margin: 0;
    background-color: #73aa83;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    transition: all 0.15s ease-in-out;
    cursor: pointer;
}

button:hover {
    background-color: #4b8d5e;
    box-shadow: 0px 0px 10px rgb(38, 38, 38);
    transition: all 0.15s ease-in-out;
}

button:disabled {
    background-color: #8a8a8a;
}
</style>