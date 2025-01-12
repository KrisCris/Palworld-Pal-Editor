<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import PathPicker from '@/components/PathPicker.vue';
const palStore = usePalEditorStore()
</script>

<template>
    <div id="entryDiv">
        <PathPicker />
        <div class="left">
            <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
            <p>{{ palStore.getTranslatedText('EntryView_Greet_1') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_2') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_3') }}</p>
            <br>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_4') }}
                <a target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor/releases">GitHub Releases</a>
                {{ palStore.getTranslatedText('EntryView_Greet_4_1') }}
                <a target="_blank" href="https://www.nexusmods.com/palworld/mods/995?tab=files">Nexus Mods</a>
                {{ palStore.getTranslatedText('EntryView_Period') }}
            </p>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_6') }}
                <a target="_blank"
                    href="https://github.com/KrisCris/Palworld-Pal-Editor/blob/develop/keep_this_project_alive.md"
                    @click="palStore.SHOW_DONATE_FLAG = true">Donate</a>
                {{ palStore.getTranslatedText('EntryView_Greet_5') }}
            </p>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_7') }}
                <a target="_blank" href="https://discord.gg/FnuA95nMJ8">Discord</a>
                {{ palStore.getTranslatedText('EntryView_Greet_7_1') }}
                <a target="_blank" href="https://github.com/KrisCris/Palworld-Pal-Editor">GitHub Repo</a>
                {{ palStore.getTranslatedText('EntryView_Period') }}
            </p>
            <p>{{ palStore.getTranslatedText('EntryView_Greet_8') }}
                <a target="_blank" href="https://space.bilibili.com/12184831">_connlost</a>
                {{ palStore.getTranslatedText('EntryView_Period') }}
            </p>
            <br>
        </div>
        <div class="right">
            <p>{{ palStore.getTranslatedText('EntryView_Note_1') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_Note_2') }}</p>
            <p>{{ palStore.getTranslatedText('EntryView_Note_3') }}</p>
            <br>
            <p class="small">{{ palStore.PAL_GAME_SAVE_PATH }}</p>
            <input type="text" v-model="palStore.PAL_GAME_SAVE_PATH"
                placeholder="C:\Users\[Username]\AppData\Local\Pal\Saved\SaveGames\[SteamID]\[SaveID]"
                :disabled="palStore.LOADING_FLAG">

            <button class="pathSelect" @click="palStore.show_file_picker">
                {{ palStore.getTranslatedText('EntryView_BTN_Path_Picker') }}
            </button>
            <button @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG">
                {{ palStore.getTranslatedText('EntryView_BTN_Load') }}
            </button>
        </div>
        <div class="version-container">
            <p class="version-info">VERSION: {{ palStore.VERSION }}</p>
            <p v-if="!palStore.IS_OFFICIAL_BUILD" class="version-warning">
                {{ palStore.getTranslatedText("EntryView_Version_Warning") }}
            </p>
        </div>
    </div>
</template>

<style scoped>
a {
    color: aquamarine;
    font-weight: bold;
    font-size: 1.5rem;
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

/* Style for the version container */
.version-container {
    position: fixed;
    bottom: 10px;
    right: 10px;
    text-align: right;
}

/* Style for the version text */
.version-info {
    font-size: 0.9rem;
    color: #868686;
    opacity: 0.7;
}

/* Style for the version warning */
.version-warning {
    font-size: 0.8rem;
    color: red;
    font-weight: bold;
}
</style>