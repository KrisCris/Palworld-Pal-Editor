<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { ref, computed, reactive, onMounted, nextTick, watch } from "vue";

const palStore = usePalEditorStore()

const palListContainer = ref(null);

onMounted(async () => {
    await nextTick(); // Wait for the DOM to update with the dynamic buttons
    const button = palListContainer.value.querySelector('button:not(:disabled)');
    if (button) {
        button.click(); // Simulate a click on the first enabled button
    }
    watch(async () => palStore.SELECTED_PLAYER_ID, async () => {
        await nextTick(); // Wait for the DOM to update with the dynamic buttons
        try {
            const button = palListContainer.value.querySelector('button:not(:disabled)');
            if (button) {
                button.click(); // Simulate a click on the first enabled button
            }
        } catch (error) {
            return
        }
    })
});

</script>

<template>
    <div class="flex">
        <p>PAL LIST</p>
        <div class="overflow-list" ref="palListContainer">
            <div class="overflow-container" v-for="pal in palStore.PAL_MAP.values()">
                <button :class="['pal', { 'male': pal.displayGender() == '♂️', 'female': pal.displayGender() == '♀️' }]"
                    :value="pal.InstanceId" @click="palStore.selectPal"
                    :disabled="palStore.SELECTED_PAL_ID == pal.InstanceId || palStore.LOADING_FLAG">
                    <img class="palIcon" :src="`/image/pals/${pal.IconAccessKey}`">
                    {{ pal.DisplayName }}
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
    width: 15rem;
    height: var(--sub-height);
    padding-right: 0.3rem;
    /* scrollbar */
}

div.overflow-list {
    display: flex;
    flex-direction: column;
    overflow-y: scroll;
    gap: .2rem 0rem;
}

.overflow-container {
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    max-height: 3.5rem;
    flex-shrink: 0;
    padding-bottom: 0.1rem;
    /* scrollbar */
    width: 100%;
}

img.palIcon {
    width: 2rem;
    border-radius: 50%;
}

button {
    cursor: pointer;
}

button.pal {
    display: flex;
    align-items: center;
    justify-content: left;
    white-space: nowrap;
    min-width: 100%;
    max-height: 3rem;
    padding: 0rem;
    padding-left: .3rem;
    min-height: 3rem;
    background-color: #323232;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1rem;
    text-align: left;
    transition: all 0.15s ease-in-out;
}

button.pal:hover {
    background-color: #686868;
    transition: all 0.15s ease-in-out;
}

button.pal:disabled {
    background-color: #8a8a8a;
}

button.pal:disabled:hover {
    background-color: #8a8a8a;
}

button.pal.male {
    /* background-color: #095594; */
    border-color: #095594;
    border-style: solid;
    border-width: 0.15rem;
}

button.pal.male:hover {
    background-color: #023b69;
}

button.pal.male:disabled {
    background-color: #023b69;
}

button.pal.female {
    border-color: #a13268;
    border-style: solid;
    border-width: 0.15rem;
}

button.pal.female:hover {
    background-color: #5d0b32;
}

button.pal.female:disabled {
    background-color: #5d0b32;
}
</style>