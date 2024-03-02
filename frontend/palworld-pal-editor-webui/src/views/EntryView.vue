<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

function loadSave() {

}

</script>

<template>
    <div id="entryDiv">
        <div class="left">
            <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
            <p>Hello there!</p>
            <p> > Thank you for using this tool!</p>
            <p> > If you are running this tool on web page, or from a docker container, please consider setting up a password.</p>
            <p> > This is important, especially if you are considering remote accessting this tool.</p>
            <br>

        </div>
        <div class="right">
            <p> > If you are running this program for the first time, you will need to manually enter the correct path to your
            save folder, i.e. the parent folder of Level.sav.</p>
            <p> > After a successful save loading, the path will be stored and automatically input for you the next time.</p>
            <p> > If you are running from the docker container, make sure you have mapped the directory correctly, and all you need is to enter the mapped path.</p>
            <br>
            <p class="small">{{ palStore.PAL_GAME_SAVE_PATH }}</p>
            <input type="text" v-model="palStore.PAL_GAME_SAVE_PATH"
                placeholder="/Path/To/PalServer/Pal/Saved/SaveGames/0/HEXHEXHEXHEXHEX"
                :disabled="palStore.LOADING_FLAG">
            <button @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG">Load Save</button>
        </div>
    </div>
</template>

<style scoped>
div#entryDiv {
    display: flex;
    flex-direction: row;
    padding: 3rem;
    gap: 0 3rem;
}

div.left, div.right{
    flex: 1 1 48%;
    display: flex;
    flex-direction: column;
}

p {
    word-wrap: break-word;
    font-size: 1.2rem;
    margin: 0 1rem;
}

p.small{
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

button:disabled {
    background-color: #8a8a8a;
}

button:disabled:hover {
    background-color: #8a8a8a;
}
</style>