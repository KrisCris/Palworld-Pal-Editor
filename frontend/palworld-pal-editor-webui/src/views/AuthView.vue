<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import { ref } from 'vue'
const palStore = usePalEditorStore()

const PW = ref("")
const remember = ref(false)

const unlock = async () => {
    if (await palStore.unlock(PW.value, remember.value)) PW.value = ""
}
</script>
<template>
    <form id="authDiv" @submit.prevent="unlock">
        <img alt="Vue logo" class="logo" src="@/assets/logo.ico" width="125" height="125" />
        <br>
        <p>{{ palStore.getTranslatedText("AuthView_PW_Prompt_1") }}</p>
        <p>{{ palStore.getTranslatedText("AuthView_PW_Prompt_2") }}</p>

        <label class="sr-only" for="password">{{ palStore.getTranslatedText('AuthView_Password_Label') }}</label>
        <input id="password" type="password" v-model="PW" autocomplete="current-password"
                :placeholder="palStore.getTranslatedText('AuthView_Password_Label')" :disabled="palStore.LOADING_FLAG">
        <label class="remember">
            <input type="checkbox" v-model="remember" :disabled="palStore.LOADING_FLAG">
            {{ palStore.getTranslatedText('AuthView_Remember_7_Days') }}
        </label>
        <button type="submit" :disabled="palStore.LOADING_FLAG">
            {{ palStore.getTranslatedText("AuthView_BTN_Unlock") }}
        </button>
    </form>
</template>

<style scoped>
form#authDiv {
    display: flex;
    flex-direction: column;
    padding: 20px; 
}

p {
    word-wrap: break-word;
    font-size: 1.2rem;
    margin: 0 1rem;
}

input[type="password"] {
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

input[type="password"]:focus {
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

.remember {
    display: flex;
    align-items: center;
    gap: .5rem;
    margin: 0 1rem 1rem;
}

.remember input {
    width: 1.2rem;
    height: 1.2rem;
}

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
</style>
