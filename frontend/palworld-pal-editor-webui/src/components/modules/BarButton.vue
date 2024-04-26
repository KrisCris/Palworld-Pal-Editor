<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

defineProps(['content', 'name', 'value'])
</script>

<template>
    <button :name="name" :value="value" :disabled="palStore.LOADING_FLAG">
        {{ content }}
    </button>
</template>

<style scoped>
button {
    margin-bottom: 1rem;
    height: 3rem;
    background-color: #3365da;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease-in-out;
}

button:hover {
    background-color: #1b49b4;
    transition: all 0.3s ease-in-out;
    cursor: pointer;
}

button:disabled {
    background-color: #8a8a8a;
    cursor: auto;
}
</style>