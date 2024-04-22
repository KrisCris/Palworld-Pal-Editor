<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { ref } from 'vue'
const palStore = usePalEditorStore()

const PW = ref("")

</script>
<template>
    <div id="authDiv">
        <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
        <br>
        <p>{{ palStore.getTranslatedText("AuthView_PW_Prompt_1") }}</p>
        <p>{{ palStore.getTranslatedText("AuthView_PW_Prompt_2") }}</p>
        
        <input type="password" v-model="PW"
                placeholder="PASSWORD" :disabled="palStore.LOADING_FLAG">
        <button @click="palStore.login" :disabled="palStore.LOADING_FLAG" :value="PW">
            {{ palStore.getTranslatedText("AuthView_BTN_Unlock") }}
        </button>
    </div>
</template>

<style scoped>
div#authDiv {
    display: flex;
    flex-direction: column;
    padding: 20px; 
}

p {
    word-wrap: break-word;
    font-size: 1.2rem;
    margin: 0 1rem;
}

input {
    height: 3rem;
    background-color: #34353a;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
    margin: 1rem 1rem;
}

input:focus {
    background-color: #b4b7be;
    color: rgb(0, 0, 0);
}

button {
    height: 3rem;
    background-color: #3365da;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease-in-out;
    margin: 0 1rem;
}

button:hover {
    background-color: #1b49b4;
    transition: all 0.3s ease-in-out;
    cursor: pointer;
}

button:disabled {
    background-color: #8a8a8a;
}
</style>