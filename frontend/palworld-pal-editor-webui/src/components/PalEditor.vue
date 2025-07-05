<script setup>
import { usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

function formatString(input) {
  if (!input) return input;
  // Separate the numeric part and the alphabetic suffix using a regular expression
  const match = input.match(/^(\d+)([A-Za-z]*)$/);
  if (!match) return input; // Return the input as is if it doesn't match the expected pattern

  const [, numbers, suffix] = match;

  // Pad the numeric part with leading zeros to make it at least 3 digits
  const paddedNumbers = numbers.padStart(3, '0');

  // Append the suffix if it exists; otherwise, append an empty space
  const formatted = suffix ? paddedNumbers + suffix : paddedNumbers;
  // if (suffix) {
  //   console.log(formatted)
  // }
  return formatted;
}

function filterInvalid(list) {
  return list.filter(item => {
    if (palStore.HIDE_INVALID_OPTIONS) {
      return !(item.Invalid || item.IsHuman)
    }
    return true
  })
}

const isMaxSuit = key => {
  return palStore.SELECTED_PAL_DATA.Suitabilities[key] >= 5;
};

const isMinSuit = key => {
  return palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKey]?.Suitabilities[key] ==
    palStore.SELECTED_PAL_DATA.Suitabilities[key] - (palStore.SELECTED_PAL_DATA["Rank"] >= 5 ? 1 : 0);
};

const isMaxLv = () => {
  return palStore.SELECTED_PAL_DATA.Level >= (palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL);
};

const isMinLv = () => {
  return palStore.SELECTED_PAL_DATA.Level <= 1;
};

const suitabilityIconSrc = key => {
  return key ? `/image/suitabilities/${key.split("::").pop()}` : '';
};

</script>

<template>
  <div :class="['PalEditor', { 'unref': palStore.SELECTED_PAL_DATA.Is_Unref_Pal }]">
    <div class="EditorItem item flex-v basicInfo">
      <button id="dump_btn" @click="palStore.dumpPalData" :disabled="palStore.LOADING_FLAG">
        {{ palStore.getTranslatedText("Editor_Btn_Export_Data") }}
      </button>
      <button id="dupe_btn" @click="palStore.dupePal" :disabled="palStore.LOADING_FLAG"
        v-if="!palStore.BASE_PAL_BTN_CLK_FLAG">
        {{ palStore.getTranslatedText("Editor_Btn_Dupe_Pal") }}
      </button>
      <button id="del_btn" @click="palStore.delPal" :disabled="palStore.LOADING_FLAG">
        🗑️ {{ palStore.getTranslatedText("Editor_Btn_Delete_Pal") }}
      </button>

      <img :class="['palIcon']" :src="`/image/pals/${palStore.SELECTED_PAL_DATA.IconAccessKey}`" alt="">
      <p v-if="palStore.SELECTED_PAL_DATA.Is_Unref_Pal">
        {{ palStore.getTranslatedText("Editor_Note_Ghost_Pal") }}
      </p>

      <div class="item flex-v left">
        <p class="cat">
          {{ palStore.getTranslatedText("Editor_Basic_Info") }}
        </p>
        <div class="editField">
          <p class="const" :title="palStore.SELECTED_PAL_DATA.InternalName">
            {{ palStore.getTranslatedText("Editor_Species") }}
            {{ palStore.displayPalElement(palStore.SELECTED_PAL_DATA.DataAccessKeyOG) }}
            {{ palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG]?.I18n ||
              palStore.SELECTED_PAL_DATA.DataAccessKeyOG }}
          </p>
          <!-- <p class="const"> Specie: </p> -->
          <select class="selector" name="CharacterID" v-model="palStore.SELECTED_PAL_DATA.DataAccessKey">
            <option class="" v-for="pal in filterInvalid(palStore.PAL_STATIC_DATA_LIST)" :value="pal.InternalName"
              :key="pal.InternalName" :title="pal.InternalName"> {{ `
              ${pal.Invalid || pal.IsHuman ? '⚠️' : ""}
              ${formatString(pal.SortingKey) || ""}
              ${palStore.displayPalElement(pal.InternalName)}
              ${pal.I18n}${palStore.HIDE_INVALID_OPTIONS ? '' : ` | ${pal.InternalName}`}`
              }} </option>
          </select>
          <button class="edit" @click="palStore.SELECTED_PAL_DATA.changeSpecie" name="CharacterID"
            :disabled="palStore.LOADING_FLAG">✅</button>

        </div>
        <div class="editField">
          <p class="const">
            {{ palStore.getTranslatedText("Editor_Nickname") }}
          </p>
          <input class="edit" type="text" name="NickName" v-model="palStore.SELECTED_PAL_DATA.NickName"
            :placeholder="palStore.SELECTED_PAL_DATA.I18nName">
          <button class="edit" @click="palStore.updatePal" name="NickName" :value="palStore.SELECTED_PAL_DATA.NickName"
            :disabled="palStore.LOADING_FLAG">✅</button>
        </div>
        <div class="flex-h">
          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.Gender">
            <p class="const">
              {{ palStore.getTranslatedText("Editor_Gender") }}
              {{ palStore.SELECTED_PAL_DATA.displayGender() }}
            </p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapGender" name="Gender"
              :disabled="palStore.LOADING_FLAG">🔄</button>
          </div>

          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.IsPal">
            <p class="const">
              {{ palStore.getTranslatedText("Editor_Variant") }}
              {{ palStore.SELECTED_PAL_DATA.displaySpecialType() }}
            </p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapTower" name="IsTower"
              v-if="palStore.SELECTED_PAL_DATA.HasTowerVariant" :disabled="palStore.LOADING_FLAG">🗼</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapBoss" name="IsBOSS"
              :disabled="palStore.LOADING_FLAG">💀</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.swapRare" name="IsRarePal"
              :disabled="palStore.LOADING_FLAG">✨</button>
          </div>

          <div class="editField" v-if="palStore.SELECTED_PAL_DATA.Level">
            <p class="const"> Lv: {{ palStore.SELECTED_PAL_DATA.Level }}</p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.levelDown" name="Level"
              :disabled="palStore.LOADING_FLA || isMinLv()">🔽</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.levelUp" name="Level"
              :disabled="palStore.LOADING_FLAG || isMaxLv()">🔼</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.maxLevel" name="Level"
              :disabled="palStore.LOADING_FLAG || isMaxLv()">🔝</button>
          </div>
        </div>
        <p class="const">
          🆔 {{ palStore.getTranslatedText("Editor_Pal_ID") }}
          {{ palStore.SELECTED_PAL_ID }}
        </p>
        <p class="const">
          🏘️ {{ palStore.getTranslatedText("Editor_Pal_Guild_ID") }}
          {{ palStore.SELECTED_PAL_DATA.group_id }}
        </p>
        <div class="editField">
          <p :class="['const', { 'out_of_container': !palStore.SELECTED_PAL_DATA.in_owner_palbox }]"
            :title="palStore.SELECTED_PAL_DATA.in_owner_palbox ? '' : 'Pal is out of owner palbox, i.e. in viewing cage or taken by someone.'">
            📦 {{ palStore.getTranslatedText("Editor_Pal_Slot") }}
            {{ palStore.SELECTED_PAL_DATA.ContainerId }} @
            {{ palStore.SELECTED_PAL_DATA.SlotIndex }}
          </p>
          <button class="edit edit_text" @click="palStore.updatePal" name="in_owner_palbox"
            :disabled="palStore.LOADING_FLAG" v-if="!palStore.SELECTED_PAL_DATA.in_owner_palbox">
            {{ palStore.getTranslatedText("Editor_Btn_Retrieve_Pal") }}
          </button>
        </div>

        <p class="const">
          🗿 {{ palStore.getTranslatedText("Editor_Pal_Owner") }}
          {{ palStore.SELECTED_PAL_DATA.OwnerName ||
            palStore.getTranslatedText("Editor_Pal_No_Owner") }}
        </p>
        <div class="palInfo" v-if="palStore.SELECTED_PAL_DATA.IsPal">
          <p class="const">
            ❤️ {{ palStore.getTranslatedText("Editor_Estimated_HP") }}
            {{ palStore.SELECTED_PAL_DATA.ComputedMaxHP / 1000 }}
          </p>
          <p class="const">
            ⚔️ {{ palStore.getTranslatedText("Editor_Estimated_ATK") }}
            {{ palStore.SELECTED_PAL_DATA.ComputedAttack }}
          </p>
          <p class="const">
            🛡️ {{ palStore.getTranslatedText("Editor_Estimated_DEF") }}
            {{ palStore.SELECTED_PAL_DATA.ComputedDefense }}
          </p>
          <p class="const">
            🔨 {{ palStore.getTranslatedText("Editor_Estimated_WorkSpeed") }}
            {{ palStore.SELECTED_PAL_DATA.ComputedCraftSpeed }}
          </p>
        </div>

        <div class="editField" v-if="palStore.SELECTED_PAL_DATA.HasWorkerSick">
          <button class="edit text" @click="palStore.updatePal" name="HasWorkerSick" :disabled="palStore.LOADING_FLAG">
            💊 {{ palStore.getTranslatedText("Editor_Btn_Heal_Pal") }}
          </button>
        </div>
        <div class="editField" v-if="palStore.SELECTED_PAL_DATA.IsFaintedPal">
          <button class="edit text" @click="palStore.updatePal" name="IsFaintedPal" :disabled="palStore.LOADING_FLAG">
            💉 {{ palStore.getTranslatedText("Editor_Btn_Revive_Pal") }}
          </button>
        </div>
      </div>
    </div>
    <div class="EditorItem flex-v item left">
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_IV") }}
      </p>
      <div class="editField spaceBetween">
        <p class="const">
          ❤️ {{ palStore.getTranslatedText("Editor_IV_HP") }}
          {{ palStore.SELECTED_PAL_DATA.Talent_HP }}
        </p>
        <input class="slider" type="range" name="Talent_HP" min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
          :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_HP" @mouseup="palStore.updatePal"
          @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">
          🛡️ {{ palStore.getTranslatedText("Editor_IV_DEF") }}
          {{ palStore.SELECTED_PAL_DATA.Talent_Defense }}
        </p>
        <input class="slider" type="range" name="Talent_Defense" min="0"
          :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255" :disabled="palStore.LOADING_FLAG"
          v-model="palStore.SELECTED_PAL_DATA.Talent_Defense" @mouseup="palStore.updatePal"
          @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">
          ⚔️ {{ palStore.getTranslatedText("Editor_IV_ATK") }}
          {{ palStore.SELECTED_PAL_DATA.Talent_Shot }}
        </p>
        <input class="slider" type="range" name="Talent_Shot" min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
          :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_Shot"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween" v-if="!palStore.HIDE_INVALID_OPTIONS">
        <p class="const">
          {{ palStore.getTranslatedText("Editor_IV_MELEE") }}
          {{ palStore.SELECTED_PAL_DATA.Talent_Melee }}
        </p>
        <input class="slider" type="range" name="Talent_Melee" min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
          :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_Melee"
          @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <hr>
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Souls_Upgrade") }}
      </p>
      <div class="editField spaceBetween">
        <p class="const">
          ❤️ {{ palStore.getTranslatedText("Editor_Souls_HP") }}
          {{ palStore.SELECTED_PAL_DATA.Rank_HP }}
        </p>
        <input class="slider" type="range" name="Rank_HP" min="0"
          :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" :disabled="palStore.LOADING_FLAG"
          v-model="palStore.SELECTED_PAL_DATA.Rank_HP" @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">
          ⚔️ {{ palStore.getTranslatedText("Editor_Souls_ATK") }}
          {{ palStore.SELECTED_PAL_DATA.Rank_Attack }}
        </p>
        <input class="slider" type="range" name="Rank_Attack" min="0"
          :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" :disabled="palStore.LOADING_FLAG"
          v-model="palStore.SELECTED_PAL_DATA.Rank_Attack" @mouseup="palStore.updatePal" @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">
          🛡️ {{ palStore.getTranslatedText("Editor_Souls_DEF") }}
          {{ palStore.SELECTED_PAL_DATA.Rank_Defence }}
        </p>
        <input class="slider" type="range" name="Rank_Defence" min="0"
          :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" :disabled="palStore.LOADING_FLAG"
          v-model="palStore.SELECTED_PAL_DATA.Rank_Defence" @mouseup="palStore.updatePal"
          @touchend="palStore.updatePal">
      </div>
      <div class="editField spaceBetween">
        <p class="const">
          🔨 {{ palStore.getTranslatedText("Editor_Souls_CraftSpeed") }}
          {{ palStore.SELECTED_PAL_DATA.Rank_CraftSpeed }}
        </p>
        <input class="slider" type="range" name="Rank_CraftSpeed" min="0"
          :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" :disabled="palStore.LOADING_FLAG"
          v-model="palStore.SELECTED_PAL_DATA.Rank_CraftSpeed" @mouseup="palStore.updatePal"
          @touchend="palStore.updatePal">
      </div>
      <hr>
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Condenser") }}
      </p>
      <div class="editField spaceBetween">
        <p class="const">
          ⭐ {{ palStore.getTranslatedText("Editor_Condenser_Rank") }}
          {{ palStore.SELECTED_PAL_DATA.Rank - 1 }}
        </p>
        <input class="slider" type="range" name="Rank" min="1" :max="palStore.HIDE_INVALID_OPTIONS ? 5 : 255"
          v-model="palStore.SELECTED_PAL_DATA.Rank" :disabled="palStore.LOADING_FLAG" @mouseup="palStore.updatePal"
          @touchend="palStore.updatePal">
      </div>
    </div>
    <div class="EditorItem flex-v item left skillPanel"
      v-if="palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKey]?.Suitabilities">
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Suitabilities") }}
      </p>
      <div class="flex-h">
        <div class="editField skillList">
          <div v-for="(value, key) in palStore.SELECTED_PAL_DATA.Suitabilities"
            v-show="palStore.HIDE_INVALID_OPTIONS || value != 'EPalWorkSuitability::OilExtraction'">
            <p class="const">
              <img :class="['suitIcon']" :src="suitabilityIconSrc(key)" alt="">
              {{ value }}
            </p>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.suitDown" :name="key"
              :disabled="palStore.LOADING_FLAG || isMinSuit(key)">🔽</button>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.suitUp" :name="key"
              :disabled="palStore.LOADING_FLAG || isMaxSuit(key)">🔼</button>
          </div>
        </div>
      </div>
    </div>
    <div class="EditorItem item flex-v left skillPanel">
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Passive_Skills") }}
      </p>
      <div class="flex-h">
        <div class="editField skillList">
          <div v-for="skill in palStore.SELECTED_PAL_DATA.PassiveSkillList">
            <div class="tooltip-container">
              <p class="const" :title="palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill">
                {{ palStore.displayRating(palStore.PASSIVE_SKILLS[skill]?.Rating) }} {{
                  palStore.PASSIVE_SKILLS[skill]?.I18n[0] || skill }}
              </p>
              <span class="tooltip-text">{{ palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill }}</span>
            </div>

            <button class="edit del" @click="palStore.SELECTED_PAL_DATA.pop_PassiveSkillList" :name="skill"
              :disabled="palStore.LOADING_FLAG">❌</button>
          </div>
          <div class="editField"
            v-if="!palStore.HIDE_INVALID_OPTIONS || palStore.SELECTED_PAL_DATA.PassiveSkillList.length < 4">
            <select class="PassiveSkill selector" name="add_PassiveSkillList"
              v-model="palStore.PAL_PASSIVE_SELECTED_ITEM">
              <option class="PassiveSkill" value="" key="">
                {{ palStore.getTranslatedText("Editor_Select_Skill") }}
              </option>
              <option class="PassiveSkill" v-for="skill in palStore.PASSIVE_SKILLS_LIST" :value="skill.InternalName"
                :key="skill.InternalName" :title="skill.I18n[1]">{{ palStore.displayRating(skill.Rating) }} {{
                  skill.I18n[0] }}</option>
            </select>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.add_PassiveSkillList" name="add_PassiveSkillList"
              :disabled="palStore.LOADING_FLAG || palStore.SELECTED_PAL_DATA.isEquippedPassiveSkill(palStore.PAL_PASSIVE_SELECTED_ITEM)">➕</button>
          </div>
        </div>
      </div>
      <hr>
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Equipped_Skills") }}
      </p>
      <div class="flex-h">
        <div class="editField skillList">
          <div v-for="skill in palStore.SELECTED_PAL_DATA.EquipWaza">
            <div class="tooltip-container">
              <p class="const" :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">{{
                palStore.displayElement(palStore.ACTIVE_SKILLS[skill]?.Element) }} {{
                  palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill
                }}
              </p>
              <span class="tooltip-text">
                <h3>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</h3>
                <p>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[1] || "" }}</p>
                <p> --- </p>
                <p>
                  {{ palStore.getTranslatedText("Editor_Skill_ATK") }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.Power }} |
                  {{ palStore.getTranslatedText("Editor_Skill_CD") }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.CT }}
                </p>
                <p>
                  {{ palStore.getTranslatedText("Editor_Skill_EL") }}
                  {{ palStore.displayElement(palStore.ACTIVE_SKILLS[skill]?.Element) }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.Element }}
                </p>
                <p>
                  {{ palStore.ACTIVE_SKILLS[skill]?.IsUniqueSkill ? "✨ Unique" : "" }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.HasSkillFruit ? "🍐 Fruit Available" : "" }}
                </p>
              </span>
            </div>

            <button class="edit del" @click="palStore.SELECTED_PAL_DATA.pop_EquipWaza" :name="skill"
              :disabled="palStore.LOADING_FLAG">❌</button>
          </div>
        </div>
      </div>
      <hr>
      <p class="cat">
        {{ palStore.getTranslatedText("Editor_Mastered_Skills") }}
      </p>
      <div class="flex-h">
        <div class="editField skillList">
          <div v-for="skill in palStore.SELECTED_PAL_DATA.MasteredWaza">
            <div class="tooltip-container">
              <p class="const" :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">
                {{ palStore.displayElement(palStore.ACTIVE_SKILLS[skill]?.Element) }}
                {{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}
              </p>
              <span class="tooltip-text">
                <h3>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</h3>
                <p>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[1] || "" }}</p>
                <p> --- </p>
                <p>
                  {{ palStore.getTranslatedText("Editor_Skill_ATK") }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.Power }} |
                  {{ palStore.getTranslatedText("Editor_Skill_CD") }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.CT }}
                </p>
                <p>
                  {{ palStore.getTranslatedText("Editor_Skill_EL") }}
                  {{ palStore.displayElement(palStore.ACTIVE_SKILLS[skill]?.Element) }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.Element }}
                </p>
                <p>
                  {{ palStore.ACTIVE_SKILLS[skill]?.IsUniqueSkill ? "✨ Unique" : "" }}
                  {{ palStore.ACTIVE_SKILLS[skill]?.HasSkillFruit ? "🍐 Fruit Available" : "" }}
                </p>
              </span>
            </div>
            <button v-if="!palStore.SELECTED_PAL_DATA.isEquippedSkill(skill)
              && (!palStore.SELECTED_PAL_DATA.isEquipSkillFull() || !palStore.HIDE_INVALID_OPTIONS)" class="edit"
              @click="palStore.SELECTED_PAL_DATA.add_EquipWaza" :name="skill"
              :disabled="palStore.LOADING_FLAG">🔼</button>
            <button class="edit del" @click="palStore.SELECTED_PAL_DATA.pop_MasteredWaza" :name="skill"
              :disabled="palStore.LOADING_FLAG">❌</button>
          </div>
          <div class="editField">
            <select class="selector" name="add_MasteredWaza" v-model="palStore.PAL_ACTIVE_SELECTED_ITEM">
              <option value="" key="">
                {{ palStore.getTranslatedText("Editor_Select_Skill") }}
              </option>
              <option v-for="skill in filterInvalid(palStore.ACTIVE_SKILLS_LIST)" :value="skill.InternalName"
                :key="skill.InternalName" :title="skill.I18n[1]">
                {{ `${palStore.displayElement(skill.Element)} ${skill.I18n[0]} ${palStore.skillIcon(skill.InternalName)}
                -
                ⚔️ ${skill.Power} - ⏱️ ${skill.CT}${palStore.HIDE_INVALID_OPTIONS ? '' : ` | ${skill.InternalName}`}` }}
              </option>
            </select>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.add_MasteredWaza" name="add_MasteredWaza"
              :disabled="palStore.LOADING_FLAG || palStore.SELECTED_PAL_DATA.isMasteredSkill(palStore.PAL_ACTIVE_SELECTED_ITEM)">➕</button>
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

.PalEditor.unref {
  filter: grayscale(100%);
}

.EditorItem {
  display: flex;
  flex-shrink: 0;
  background: #484848;
  padding: 1.5rem;
  border-radius: 1rem;
}

/* .EditorItem .Basic-Info {} */

/* option.PassiveSkill{
  background-color: red;
} */

div.basicInfo {
  position: relative;
  max-width: calc(var(--editor-panel-width) - 380px);
  min-width: 600px;
}

div.palInfo {
  display: flex;
  flex-wrap: wrap;
}

div.skillPanel {
  max-width: var(--editor-panel-width);
  flex-wrap: wrap;
}

div.skillList {
  display: flex;
  flex-wrap: wrap;
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

/* div.item {
  margin: .5rem;
} */

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

p.out_of_container {
  color: #3db15e !important;
}

img.palIcon {
  max-width: 15vh;
  border-radius: 50%;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  margin-bottom: 1rem;
}

img.suitIcon {
  height: 1.8rem;
  margin: .2rem;
  padding: .2rem .2rem;
}

img.palIcon.unref {
  filter: grayscale(100%);
}

div.editField {
  /* border-style: dashed;
  border-width: 1px;
  border-color: white; */
  /* width: 100%; */
  /* flex-wrap: nowrap; */
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

button#dump_btn {
  position: absolute;
  top: 1rem;
  left: 1rem;

  display: flex;
  align-items: center;
  justify-content: center;
  height: 2rem;
  padding: 1rem;
  margin: 0rem;
  background-color: #636363;
  color: rgb(204, 204, 204);
  border: none;
  outline: none;
  border-radius: 0.5rem;
  transition: all 0.15s ease-in-out;
}

button#dump_btn:hover {
  background-color: #3e3e3e;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  color: rgb(204, 204, 204);
}

button#dump_btn:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button#del_btn {
  position: absolute;
  top: 1rem;
  right: 1rem;

  display: flex;
  align-items: center;
  justify-content: center;
  height: 2rem;
  padding: 1rem;
  margin: 0rem;
  background-color: #bd1c3c;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  transition: all 0.15s ease-in-out;
}

button#del_btn:hover {
  background-color: #830e25;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
}

button#del_btn:disabled {
  background-color: #8a8a8a;
  box-shadow: 0 0 0;
  filter: grayscale(100%);
  cursor: not-allowed;
}

button#dupe_btn {
  position: absolute;
  top: 3.5rem;
  left: 1rem;

  display: flex;
  align-items: center;
  justify-content: center;
  height: 2rem;
  padding: 1rem;
  margin: 0rem;
  background-color: #1c8dbd;
  color: whitesmoke;
  border: none;
  outline: none;
  border-radius: 0.5rem;
  transition: all 0.15s ease-in-out;
}

button#dupe_btn:hover {
  background-color: #0e6b92;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
}

button#dupe_btn:disabled {
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
</style>