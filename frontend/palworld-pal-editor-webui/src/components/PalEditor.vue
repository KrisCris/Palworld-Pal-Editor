<script setup>
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()


</script>

<template>
  <div class="grid">
    <div class="item flex-v">
      <img class="palIcon" :src="`/image/pals/${palStore.SELECTED_PAL_DATA.IconAccessKey}`" alt="">
      <div class="item flex-v left">
        <p class="cat">BASIC INFO</p>
        <div class="editField">
          <p class="const"> NickName: </p>
          <input class="edit" type="text" name="NickName" v-model="palStore.SELECTED_PAL_DATA.NickName"
            :placeholder="palStore.SELECTED_PAL_DATA.I18nName">
          <button class="edit" @click="palStore.updatePal" name="NickName">✅</button>
        </div>
        <div class="flex-h">
          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.Gender">
            <p class="const"> Gender: {{ palStore.SELECTED_PAL_DATA.displayGender() }}</p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapGender" name="Gender">🔄</button>
          </div>

          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.IsPal">
            <p class="const"> Variant: {{ palStore.SELECTED_PAL_DATA.displaySpecialType() }}</p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapTower" name="IsTower"
              v-if="palStore.SELECTED_PAL_DATA.HasTowerVariant">🗼</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapBoss" name="IsBOSS">💀</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapRare" name="IsRarePal">✨</button>
          </div>

          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.Level">
            <p class="const"> Lv: {{ palStore.SELECTED_PAL_DATA.Level }}</p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.levelDown" name="Gender">🔽</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.levelUp" name="Gender">🔼</button>
          </div>
        </div>
        <p class="const">Pal Instance ID: {{ palStore.SELECTED_PAL_ID }}</p>
        <p class="const">Owner: {{ palStore.SELECTED_PAL_DATA.OwnerName || "None (BASE WORKER)" }}</p>
        <p class="const">❤️ MaxHP: {{ palStore.SELECTED_PAL_DATA.MaxHP / 1000 }}</p>
        <p class="const">⚔️ Possible Attack: {{ palStore.SELECTED_PAL_DATA.ComputedAttack }}</p>
        <p class="const">🛡️ Possible Defense: {{ palStore.SELECTED_PAL_DATA.ComputedDefense }}</p>
        <div class="editField" v-if="!palStore.SELECTED_PAL_DATA.HasWorkerSick">
          <button class="edit text" @click="palStore.updatePal" name="HasWorkerSick">💊 Clear Worker Sick</button>
        </div>
      </div>
    </div>
    <div class="flex-v item left">
      <p class="cat">IVs</p>
      <div class="editField spaceBetween">
        <p class="const">HP IV: {{ palStore.SELECTED_PAL_DATA.Talent_HP }}</p>
        <input type="range" name="Talent_HP" min="0" max="100" v-model="palStore.SELECTED_PAL_DATA.Talent_HP"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">DEF IV: {{ palStore.SELECTED_PAL_DATA.Talent_Defense }}</p>
        <input type="range" name="Talent_Defense" min="0" max="100" v-model="palStore.SELECTED_PAL_DATA.Talent_Defense"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">ATK IV: {{ palStore.SELECTED_PAL_DATA.Talent_Shot }}</p>
        <input type="range" name="Talent_Shot" min="0" max="100" v-model="palStore.SELECTED_PAL_DATA.Talent_Shot"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">MELEE IV (Unused): {{ palStore.SELECTED_PAL_DATA.Talent_Melee }}</p>
        <input type="range" name="Talent_Melee" min="0" max="100" v-model="palStore.SELECTED_PAL_DATA.Talent_Melee"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <hr>
      <p class="cat">SOUL RANKs (POWER STATUE)</p>
      <div class="editField spaceBetween">
        <p class="const">SoulBonus HP: {{ palStore.SELECTED_PAL_DATA.Rank_HP }}</p>
        <input type="range" name="Rank_HP" min="0" max="10" v-model="palStore.SELECTED_PAL_DATA.Rank_HP"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">SoulBonus Attack: {{ palStore.SELECTED_PAL_DATA.Rank_Attack }}</p>
        <input type="range" name="Rank_Attack" min="0" max="10" v-model="palStore.SELECTED_PAL_DATA.Rank_Attack"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">SoulBonus Defence: {{ palStore.SELECTED_PAL_DATA.Rank_Defence }}</p>
        <input type="range" name="Rank_Defence" min="0" max="10" v-model="palStore.SELECTED_PAL_DATA.Rank_Defence"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">SoulBonus CraftSpeed: {{ palStore.SELECTED_PAL_DATA.Rank_CraftSpeed }}</p>
        <input type="range" name="Rank_CraftSpeed" min="0" max="10" v-model="palStore.SELECTED_PAL_DATA.Rank_CraftSpeed"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <hr>
      <p class="cat">CONDENSER RANK</p>
      <div class="editField spaceBetween">
        <p class="const">Condenser Rank: {{ palStore.SELECTED_PAL_DATA.Rank - 1 }}</p>
        <input type="range" name="Rank" min="1" max="5" v-model="palStore.SELECTED_PAL_DATA.Rank"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
    </div>
    <div class="item flex-v left">
      <p class="cat">PASSIVE SKILLS</p>
      <div class="flex-h">
        <div class="editField">
          <div v-for="skill in palStore.SELECTED_PAL_DATA.PassiveSkillList">
            <p class="const">{{ skill }}</p>
            <button class="edit del" @click="palStore.SELECTED_PAL_DATA.removePassiveSkill" :name="skill">❌</button>
          </div>
        </div>
      </div>
      <div class="editField">
        <select name="AddPassiveSkill">
          <option value="">{{ display }}</option>
        </select>
        <button v-if="palStore.SELECTED_PAL_DATA.PassiveSkillList.length < 4" class="edit"
          @click="palStore.SELECTED_PAL_DATA.removePassiveSkill" :name="skill">➕</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
hr {
  border: 0;
  /* Remove the default border */
  width: 100%;
  height: 2px;
  /* Set the height of the divider */
  background-color: #8a8a8a;
  /* Set the divider color */
  margin: 20px 0;
  /* Add some vertical spacing around the divider */
}

p.cat {
  margin-top: -.8rem;
  margin-left: -.5rem;
}

.grid {
  display: flex;
  /* grid-template-columns: repeat(auto-fill, minmax(25vh, 1fr)); */
  /* This is better for small screens, once min() is better supported */
  /* grid-template-columns: repeat(auto-fill, minmax(min(200px, 100%), 1fr)); */
  /* gap: 1rem;

  padding-right: 2rem; */
  height: calc(100vh - 4rem);
  overflow-y: auto;
  flex-wrap: wrap;
  align-items: flex-start
}

div {
  display: flex;
  align-items: center;
}

div.item {
  margin: .5rem;
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

.grid>div {
  background: #484848;
  padding: 1.5rem;
  border-radius: 1rem;
}

img.palIcon {
  max-width: 15vh;
  border-radius: 50%;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  margin-bottom: 1rem;
}

div.editField {
  /* border-style: dashed;
  border-width: 1px;
  border-color: white; */
  /* width: 100%; */
  gap: 5px
}

button.edit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0rem;
  margin: 0rem;
  background-color: #73aa83;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  transition: all 0.3s ease-in-out;
}

button.edit:hover {
  background-color: #4b8d5e;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
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

button.del {
  background-color: #ffcece;
}

button.del:hover {
  background-color: #7c0f0f;
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
</style>