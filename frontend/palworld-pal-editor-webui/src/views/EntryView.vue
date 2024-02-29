<script setup>
import {usePalEditorStore} from '@/stores/paleditor'
const palStore = usePalEditorStore()

function loadSave() {
  
}

</script>
<template>
    <div>
        <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
        <h1>Hello there!</h1>
        <h2>it seems you are not launching from the docker container, or properly setting up the save path.</h2>
        <br><br>
    </div>
    <div>
        <h3>If you are launching from the executable, please enter the correct path to your save folder. </h3>
        <p>(The parent folder of Level.sav)</p>
        <br>
        <div>
            <p>{{ palStore.PAL_SAVE_PATH }}</p>
            <input type="text" v-model="palStore.PAL_SAVE_PATH">
            <button @click="palStore.loadSave" :disabled="palStore.LOADING_FLAG">Load Save</button>
        </div>
    </div>
</template>
<style scoped>
input {
    margin-bottom: 1rem;
    width: 100%;
    height: 3rem;
    background-color: #4a4e57;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
}
button{
    margin-bottom: 1rem;
    width: 100%;
    height: 3rem;
    background-color: #3365da;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease-in-out;
}

button:hover{
    background-color: #1b49b4;
    transition: all 0.3s ease-in-out;
}
</style>