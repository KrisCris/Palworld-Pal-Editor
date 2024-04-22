<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { computed } from '@vue/reactivity';
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
</script>

<template>
    <div v-if="palStore.SHOW_FILE_PICKER" class="popup">
        <p> {{ palStore.PAL_GAME_SAVE_PATH }}</p>
        <span>Current Directory: </span>
        <input class="pathInput" type="text" name="PAL_GAME_SAVE_PATH" id="PAL_GAME_SAVE_PATH"
            v-model="palStore.PAL_GAME_SAVE_PATH">
        <button @click="palStore.update_picker_result(palStore.PAL_GAME_SAVE_PATH)">GO</button>
        <ul>
            <li v-for="([key, value], index) of sortedPathChildren" :key="index" :isdir="value.isDir"
                @click="palStore.update_picker_result(key)" :fullpath="key">
                {{ value.isDir ? "📁" : "📄" }} {{ value.filename }}
            </li>
        </ul>
        <button @click="palStore.path_back">Back</button>
        <button @click="palStore.SHOW_FILE_PICKER = false">OK</button>
    </div>
</template>

<style scoped>
.popup {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    padding: 20px;
    background-color: #515151;
    z-index: 10;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.popup .pathInput {
    width: 70%;
}

.popup ul {
    max-height: 200px;
    overflow-y: auto;
    list-style-type: none;
    padding: 0;
    border: 1px solid #ccc;
    margin-top: 10px;
}

.popup li {
    margin: 5px 0;
}

.popup button {
    display: block;
    margin-top: 10px;
}
</style>