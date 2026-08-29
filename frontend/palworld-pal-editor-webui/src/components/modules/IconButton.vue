<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import UiIcon from './UiIcon.vue'
const palStore = usePalEditorStore()

defineProps({
    icon: { type: String, required: true },
    label: { type: String, required: true },
    name: { type: String, default: undefined },
    value: { type: String, default: undefined },
})
defineEmits([])
</script>

<template>
    <button :name="name" :value="value" :aria-label="label">
        <UiIcon :name="icon" />
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
