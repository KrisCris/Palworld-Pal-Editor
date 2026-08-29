<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { useSessionStore } from '@/stores/session'
import { computed } from '@vue/reactivity';
import { ref, onMounted } from 'vue'

import IconButton from './modules/IconButton.vue';
import UiIcon from './modules/UiIcon.vue';
import InputArea from './modules/InputArea.vue'
import BarButton from './modules/BarButton.vue'
const palStore = usePalEditorStore()
const sessionStore = useSessionStore()

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
    sessionStore.savePath = palStore.PAL_FILE_PICKER_PATH

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
const abort = () => {
    palStore.SHOW_FILE_PICKER = false
}
</script>

<template>
    <div class="modal-overlay editor-modal-overlay" v-if="palStore.SHOW_FILE_PICKER" @pointerdown.self="abort">
        <div class="popup editor-glass-surface">
            <button class="close-btn" @click="abort">×</button>
            <div class="currentPath">
                <IconButton icon="back" :label="palStore.getTranslatedText('PathPicker_Back')" @click="palStore.path_back" />
                <InputArea v-model="palStore.PAL_FILE_PICKER_PATH" />
                <IconButton icon="forward" :label="palStore.getTranslatedText('PathPicker_Open')"
                    @click="palStore.update_picker_result(palStore.PAL_FILE_PICKER_PATH)" />
            </div>

            <ul ref="scrollElement">
                <li v-for="([key, value], index) of sortedPathChildren" :key="index" :isdir="value.isDir"
                    @click="() => { if (value.isDir) palStore.update_picker_result(key) }" :fullpath="key">
                    <UiIcon :name="value.isDir ? 'folder' : 'file'" /> {{ value.filename }}
                </li>
            </ul>
            <BarButton @click="savePickerResult" content="OK" :disabled="!palStore.IS_PAL_SAVE_PATH" />
        </div>
    </div>
</template>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.popup {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

    border: 1px solid var(--editor-color-glass-border);
    outline: none;
    width: 75vw;
    height: 75vh;

    border-radius: 0.5rem;
    padding: 2rem 4rem;
    z-index: 10;

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
    color: var(--editor-color-text);
}

.popup li:hover[isdir=true] {
    background-color: var(--editor-color-control-hover);
}

.close-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    background: color-mix(in srgb, var(--editor-color-control-hover) 70%, transparent);
    border-radius: 25%;
    width: 30px;
    height: 30px;
    border: none;
    color: var(--editor-color-text);
    font-size: 1.5rem;
    cursor: pointer;
}

.close-btn:hover {
    background: var(--editor-color-control-hover);
    color: var(--editor-color-danger);
}
</style>
