<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()


</script>
<template>
    <div class="flex">
        <div class="overflow-container" v-for="pal in palStore.PAL_MAP.values()">
            <button :class="[{ 'male': pal.displayGender() == '♂️', 'female': pal.displayGender() == '♀️' }]"
                :value="pal.InstanceId" @click="palStore.selectPal" :disabled="palStore.SELECTED_PAL_ID == pal.InstanceId">
                <img class="palIcon" :src="`/image/pals/${pal.IconAccessKey}`">
                {{ pal.DisplayName }}
            </button>
        </div>
    </div>
</template>

<style scoped>
div.flex {
    padding-top: .5rem;
    overflow-y: scroll;
    height: calc(100vh - 4rem);
    display: flex;
    flex-shrink: 0;
    flex-direction: column;
    padding-right:0.3rem;
    margin-right: .7rem;
    /* margin-top: -0.25rem; */
}

.overflow-container {
    display: flex;
    align-items: center;
    width: 15rem;
    /* Fixed width smaller than the button's content */
    overflow-x: auto;
    /* Enable horizontal scrolling */
    white-space: nowrap;
    /* Prevent content from wrapping */
    min-height: 3.5rem;
    /* padding-bottom: 1rem; */
}

img.palIcon {
    width: 2rem;
    border-radius: 50%;
}

button {
    display: flex;
    align-items: center;
    justify-content: left;

    white-space: nowrap;
    min-width: 100%;
    /* max-width: 10vw; */
    max-height: 3.5rem;
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
    transition: all 0.3s ease-in-out;
}

button:hover {
    background-color: #686868;
    transition: all 0.3s ease-in-out;
}

button.male {
    /* background-color: #095594; */
    border-color: #095594;
    border-style: solid;
    border-width: 0.15rem;
}

button.male:hover {
    background-color: #023b69;
}

button.male:disabled {
    background-color: #023b69;
}

button.female {
    border-color: #a13268;
    border-style: solid;
    border-width: 0.15rem;
}

button.female:hover {
    background-color: #5d0b32;
}

button.female:disabled {
    background-color: #5d0b32;
}</style>