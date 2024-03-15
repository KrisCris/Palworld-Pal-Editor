<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { ref, computed, reactive, onMounted, nextTick, watch } from "vue";

const palStore = usePalEditorStore()

const palListContainer = ref(null);

watch(async () => palStore.SELECTED_PLAYER_ID, async () => {
    await nextTick();
    try {
        const button = palListContainer.value.querySelector('button:not(:disabled)');
        if (button) {
            button.click();
        }
    } catch (error) {
        return
    }
})

// watch(async () => palStore.ADD_PAL_RESELECT_CTR, async () => {
//     await nextTick();
//     try {
//         const button = palListContainer.value.querySelector('button:not(:disabled)');
//         if (button) {
//             button.click();
//         }
//     } catch (error) {
//         return
//     }
// })

watch(async () => palStore.UPDATE_PAL_RESELECT_CTR, async () => {
    await nextTick();
    try {
        const button = palListContainer.value.querySelector(`button[value="${palStore.SELECTED_PAL_ID}"]`);
        if (button) {
            if (!palStore.isElementInViewport(button)) {
                button.scrollIntoView({ behavior: "smooth" });
            }
        }
    } catch (error) {
        return
    }
})

watch(async () => palStore.SELECTED_PAL_ID, async () => {
    await nextTick();
    try {
        const button = palListContainer.value.querySelector(`button[value="${palStore.SELECTED_PAL_ID}"]`);
        if (button) {
            if (palStore.SELECTED_PAL_ID != palStore.SELECTED_PAL_DATA?.InstanceId) {
                palStore.selectPal({ target: button }, true)
            }
            if (!palStore.isElementInViewport(button)) {
                button.scrollIntoView({ behavior: "smooth" });
            }
        }
    } catch (error) {
        return
    }
})

onMounted(async () => {
    await nextTick();
    // TODO Note: this is just a temp fix for pal selection when pal list is refreshed by updatePlayer
    await nextTick();
    await nextTick();
    const button = palListContainer.value.querySelector('button:not(:disabled)');
    if (button) {
        button.click();
    }
});

function get_filtered_pal_list() {
    console.log("FILTER")
    let list = Array.from(palStore.PAL_MAP.values())

    if (!palStore.SHOW_UNREF_PAL_FLAG) {
        list = list.filter(pal => !pal.Is_Unref_Pal)
    } else {
        list = list.filter(pal => pal.Is_Unref_Pal)
    }

    const player = palStore.PLAYER_MAP.get(palStore.SELECTED_PLAYER_ID)
    if (player) {
        if (!palStore.SHOW_VIEWING_CAGE_PAL_FLAG) {
            list = list.filter(pal => {
                return pal.ContainerId == player.OtomoCharacterContainerId || pal.ContainerId == player.PalStorageContainerId
            })
        } else {
            list = list.filter(pal => {
                return pal.ContainerId != player.OtomoCharacterContainerId && pal.ContainerId != player.PalStorageContainerId
            })
        }
    }

    return list
}

</script>

<template>
    <div class="flex">
        <div class="title">
            <p>PAL LIST</p>
            <button class="add_pal" v-if="!palStore.BASE_PAL_BTN_CLK_FLAG"
                :title="`Add Pal for Player ${palStore.PLAYER_MAP.get(palStore.SELECTED_PLAYER_ID).name}`"
                :disabled="palStore.LOADING_FLAG" @click="palStore.addPal" name="add_pal">+</button>
        </div>

        <div class="overflow-list" ref="palListContainer">
            <div class="overflow-container" v-for="pal in get_filtered_pal_list()">
                <button
                    :class="['pal', { 'male': pal.displayGender() == '♂️', 'female': pal.displayGender() == '♀️', 'unref': pal.Is_Unref_Pal }]"
                    :value="pal.InstanceId" @click="palStore.selectPal"
                    :disabled="palStore.SELECTED_PAL_ID == pal.InstanceId || palStore.LOADING_FLAG">
                    <img :class="['palIcon']" :src="`/image/pals/${pal.IconAccessKey}`">
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

div.title {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    gap: .5rem;
    justify-content: space-between;
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

button.unref {
    filter: grayscale(100%);
}

button.unref:hover {
    background-color: #5e5e5e !important;
}

button.unref:disabled {
    background-color: #5e5e5e !important;
}

button.add_pal {
    background-color: #3db15e;
    /* padding: 0; */
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.2rem;
    font-size: 1rem;
}

button.add_pal:hover {
    background-color: #4b8d5e;
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
    cursor: pointer;
}

button.add_pal:disabled {
    background-color: #8a8a8a;
}
</style>