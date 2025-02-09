<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
import ItemCard from '@/components/modules/TechCard.vue'

const palStore = usePalEditorStore()

const isMaxLv = () => {
    return palStore.SELECTED_PLAYER_DATA.Level >= (palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL);
};

const isMinLv = () => {
    return palStore.SELECTED_PLAYER_DATA.Level <= 1;
};
</script>

<template>
    <div class="PalEditor">
        <div class="EditorItem item flex-v basicInfo">
            <div class="item flex-v left">
                <p class="cat">
                    {{ palStore.getTranslatedText("Editor_Basic_Info") }}
                </p>
                <div class="editField">
                    <p class="const">
                        {{ palStore.getTranslatedText("Editor_Nickname") }}
                    </p>
                    <input class="edit" type="text" name="NickName" v-model="palStore.SELECTED_PLAYER_DATA.NickName">
                    <button class="edit" @click="palStore.updatePlayer" name="NickName"
                        :value="palStore.SELECTED_PLAYER_DATA.NickName" :disabled="palStore.LOADING_FLAG">✅</button>
                </div>
                <div class="editField" v-if="palStore.SELECTED_PLAYER_DATA.Level">
                    <p class="const"> Lv: {{ palStore.SELECTED_PLAYER_DATA.Level }}</p>
                    <button class="edit" @click="palStore.SELECTED_PLAYER_DATA.levelDown" name="Level"
                        :disabled="palStore.LOADING_FLA || isMinLv()">🔽</button>
                    <button class="edit" @click="palStore.SELECTED_PLAYER_DATA.levelUp" name="Level"
                        :disabled="palStore.LOADING_FLAG || isMaxLv()">🔼</button>
                    <button class="edit" @click="palStore.SELECTED_PLAYER_DATA.maxLevel" name="Level"
                        :disabled="palStore.LOADING_FLAG || isMaxLv()">🔝</button>
                </div>
            </div>
        </div>
        <!-- <div class="EditorItem flex-v item left">
            <p class="cat">
                {{ palStore.getTranslatedText("Editor_IV") }}
            </p>
        </div> -->
        <div class="EditorItem flex-h maxW">
            <div class="levels-container">
                <div class="level-row" v-for="(items, level) in palStore.TECH_LV_DICT" :key="level">
                    <div class="level-indicator">
                        Level {{ level }}
                    </div>
                    <div class="cards-row">
                        <ItemCard v-for="item in items" :key="item.InternalName" :item="item" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.PalEditor {
    display: flex;
    height: var(--sub-height);
    overflow-y: auto;
    flex-wrap: wrap;
    align-items: flex-start;
    align-content: flex-start;
    gap: .5rem;
}

.EditorItem {
    display: flex;
    flex-shrink: 0;
    background: #484848;
    padding: 1.5rem;
    border-radius: 1rem;
}

.EditorItem.maxW {
    padding: 1rem;
    max-width: var(--editor-panel-width);
}

div.editField {
    /* border-style: dashed;
    border-width: 1px;
    border-color: white; */
    /* width: 100%; */
    /* flex-wrap: nowrap; */
    gap: 5px
}

div.basicInfo {
    position: relative;
    max-width: calc(var(--editor-panel-width) - 380px);
    /* min-width: calc(max(100%,var(--editor-panel-width))); */
}

hr {
    border: 0;
    width: 100%;
    height: 2px;
    background-color: #8a8a8a;
    margin: 20px 0;
}

button {
    cursor: pointer;
}

p.cat {
    margin-top: -.8rem;
    margin-left: -.5rem;
}

div {
    display: flex;
    align-items: center;
}

div.flex-v {
    flex-direction: column;
    gap: .2rem;
}

div.flex-h {
    flex-direction: row;
    gap: .5rem
}

div.left {
    justify-content: flex-start;
    align-items: flex-start;
}

p.const {
    display: flex;
    align-items: center;
    background-color: #272727;
    height: 1.8rem;
    margin: .2rem;
    padding: .2rem .4rem;
    border-radius: .5rem;
    color: rgb(208, 212, 226);
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
}

button.edit {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    padding: 0rem;
    margin: 0rem;
    background-color: #848484;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    transition: all 0.15s ease-in-out;
}

button.edit:hover {
    background-color: #9c9c9c;
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
    transition: all 0.15s ease-in-out;
}

button.edit:disabled {
    background-color: #8b8b8b;
    box-shadow: 0 0 0;
    filter: grayscale(100%);
    cursor: not-allowed;
}

button.text {
    width: 100%;
    background-color: #2c77c2;
    padding: 1rem .5rem;
    margin: .2rem;
}

button.text:hover {
    background-color: #18518a;
}

button.text:disabled {
    background-color: #8a8a8a;
    box-shadow: 0 0 0;
    filter: grayscale(100%);
    cursor: not-allowed;
}

button.edit_text {
    width: 5rem;
    background-color: #2c77c2;
    padding: 1rem .5rem;
    margin: .2rem;
}

button.edit_text:hover {
    background-color: #18518a;
}

button.edit_text:disabled {
    background-color: #8a8a8a;
    box-shadow: 0 0 0;
    filter: grayscale(100%);
    cursor: not-allowed;
}

button.del {
    background-color: #ffcece;
}

button.del:hover {
    background-color: #7c0f0f;
}

button.del:disabled {
    background-color: #8a8a8a;
    box-shadow: 0 0 0;
    filter: grayscale(100%);
    cursor: not-allowed;
}

input.edit {
    height: 2rem;
    background-color: #6a6a6c;
    color: whitesmoke;
    border: none;
    outline: none;
    border-radius: 0.5rem;
    font-size: 1.2rem;
    padding-left: 0.7rem;
    padding-right: 0.7rem;
}

input.edit:focus {
    background-color: #b8b8b8;
    color: black;
    /* border: 2px solid #6a6a6c; */
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
}

input.edit::placeholder {
    color: #cccccca2
}

div.spaceBetween {
    display: flex;
    width: 100%;
    justify-content: space-between
}

.tooltip-container {
    position: relative;
    display: inline-block;
}

.tooltip-text {
    visibility: hidden;
    width: 200px;
    background-color: rgba(0, 0, 0, 0.85);
    color: white;
    text-align: center;
    border-radius: 6px;
    padding: 1rem;

    /* Position the tooltip */
    position: absolute;
    z-index: 1;
    bottom: 100%;
    left: 50%;
    margin-left: -60px;
    margin-bottom: .25rem;
}

.tooltip-container:hover .tooltip-text {
    visibility: visible;
}

select.selector {
    display: flex;
    align-items: center;
    background-color: #272727;
    height: 1.8rem;
    margin: .2rem;
    padding: .2rem .4rem;
    border-radius: .5rem;
    color: rgb(208, 212, 226);
    box-shadow: 2px 2px 10px rgb(38, 38, 38);
    /* max-width: 50%; */
}

.levels-container {
    display: flex;
    flex-direction: column;
    max-height: 80vh;
    overflow-y: auto;
    max-width: 100%;
    padding: 8px;
    justify-content:left;
}

.level-row {
    display: flex;
    align-items: center;
    max-width: 100%;
}

.level-indicator {
    flex: 0 0 auto;
    justify-content: center;
    min-width: 5rem;
    font-weight: bold;
    margin-right: .5rem;
    color: #fff;
    background-color: #333;
    padding: .5rem;
    border-radius: 8px;
}

.cards-row {
    flex: 1 1 auto;
    display: flex;
    max-width: 900px;
    overflow-x: auto;
}
</style>