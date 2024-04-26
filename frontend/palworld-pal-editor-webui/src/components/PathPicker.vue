<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { computed } from '@vue/reactivity';
import { ref, onMounted } from 'vue'

import IconButton from './modules/IconButton.vue';
import InputArea from './modules/InputArea.vue'
import BarButton from './modules/BarButton.vue'
const palStore = usePalEditorStore()

const sortedPathChildren = computed(() => {
    return Array.from(palStore.PATH_CONTEXT.entries()).sort((a, b) => {
        if (a[1].isDir && !b[1].isDir) {
            return -1;
        } else if (!a[1].isDir && b[1].isDir) {
            return 1;
        }

        return a[1].filename.localeCompare(b[1].filename);
    })
})

const savePickerResult = () => {
    palStore.SHOW_FILE_PICKER = false
    palStore.PAL_GAME_SAVE_PATH = palStore.PAL_FILE_PICKER_PATH

}

// const scrollElement = ref(null);

// const checkScroll = () => {
//     if (!scrollElement.value) return;
//     const scrollTop = scrollElement.value.scrollTop;
//     const scrollHeight = scrollElement.value.scrollHeight;
//     const clientHeight = scrollElement.value.clientHeight;

//     scrollElement.value.classList.toggle('scrolled-top', scrollTop > 0);
//     scrollElement.value.classList.toggle('scrolled-bottom', scrollTop + clientHeight < scrollHeight);
// };

// onMounted(() => {
//     if (scrollElement.value) {
//         scrollElement.value.addEventListener('scroll', checkScroll);
//         checkScroll(); // Initial check to update shadow state
//     }
// });
</script>

<template>
    <div class="popup">
        <div class="currentPath">
            <IconButton icon="⤴️" @click="palStore.path_back" />
            <InputArea v-model="palStore.PAL_FILE_PICKER_PATH" />
            <IconButton icon="➡️" @click="palStore.update_picker_result(palStore.PAL_FILE_PICKER_PATH)" />
        </div>

        <ul ref="scrollElement">
            <li v-for="([key, value], index) of sortedPathChildren" 
                :key="index" 
                :isdir="value.isDir"
                @click="() => { if (value.isDir) palStore.update_picker_result(key) }" 
                :fullpath="key"
            >
                {{ value.isDir ? "📁" : "📄" }} {{ value.filename }}
            </li>
        </ul>
        <BarButton @click="savePickerResult" content="OK" :disabled="!palStore.IS_PAL_SAVE_PATH" />
    </div>
</template>

<style scoped>
.popup {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

    border: none;
    outline: none;
    width: 75vw;
    height: 75vh;

    border-radius: 0.5rem;
    padding: 2rem 4rem;
    background-color: #515151;
    z-index: 10;
    box-shadow: 0 0 10px 10px rgba(0, 0, 0, 0.1);

    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.popup .currentPath {
    display: flex;
    gap: 10px;
    align-items: center;
}

.popup ul {
    overflow-y: auto;
    list-style-type: none;
    padding: 0;
    flex: 1;
}

.popup li[isdir=true] {
    cursor: pointer;
}

.popup li {
    margin: .2rem .2rem;
    padding: .3rem .3rem;
    border-radius: 0.5rem;
    color: whitesmoke;
}

.popup li:hover[isdir=true] {
    background-color: #4b8d5e;
}
</style>