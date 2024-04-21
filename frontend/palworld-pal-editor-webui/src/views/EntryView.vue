<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()
</script>

<template>
    <div id="entryDiv">
        <div class="left">
            <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
            <p>{{ palStore.getTranslatedText('EntryView_1') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_2') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_3') }}</p>
            <br>
            <p>{{ palStore.getTranslatedText('EntryView_4') }}
                <a target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor">GitHub</a>
                {{ palStore.getTranslatedText('EntryView_5') }}
            </p>
            <p>{{ palStore.getTranslatedText('EntryView_6') }}
                <a target="_blank" href="https://ko-fi.com/connlost">ko-fi</a>
                {{ palStore.getTranslatedText('EntryView_5') }}
            </p>
            <br>
        </div>
        <div class="right">
            <p>{{ palStore.getTranslatedText('EntryView_7') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_8') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_9') }}</p>
            <br>
            <p class="small">{{ palStore.PAL_GAME_SAVE_PATH }}</p>
            <input type="text" v-model="palStore.PAL_GAME_SAVE_PATH"
                placeholder="C:\Users\[Username]\AppData\Local\Pal\Saved\SaveGames\[SteamID]\[SaveID]"
                :disabled="palStore.LOADING_FLAG">

            <button class="pathSelect" @click="palStore.show_file_picker" v-if="palStore.FilePickerAvailable">
                {{ palStore.getTranslatedText('EntryView_Btn_1') }}
            </button>
            <button @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG">
                {{ palStore.getTranslatedText('EntryView_Btn_2') }}
            </button>
        </div>
    </div>
</template>

<style scoped>
a {
    color: aquamarine;
}

div#entryDiv {
    display: flex;
    flex-direction: row;
    padding: 3rem;
    gap: 0 3rem;
}

div.col {
    display: flex;
    flex-direction: column;
}

div.left,
div.right {
    max-width: 50%;
    display: flex;
    flex-direction: column;
}

p {
    word-wrap: break-word;
    font-size: 1.2rem;
    margin: 0 1rem;
}

p.small {
    font-size: 0.8rem;
    margin: 0 0;
    color: grey;
}

input {
    margin-bottom: 1rem;
    height: 3rem;
    background-color: #34353a;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
}

input:focus {
    background-color: #b4b7be;
    color: rgb(0, 0, 0);
}

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

button.pathSelect {
    margin-bottom: 1rem;
    height: 3rem;
    background-color: #3f3f3f;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease-in-out;
}

button.pathSelect:hover {
    background-color: rgb(125, 125, 125);
    transition: all 0.3s ease-in-out;
    cursor: pointer;
}

button:disabled {
    background-color: #8a8a8a;
}

button:disabled:hover {
    background-color: #8a8a8a;
}
</style>