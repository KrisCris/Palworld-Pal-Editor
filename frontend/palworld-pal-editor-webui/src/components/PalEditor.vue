<script setup>
import PalSpeciesSelector from '@/components/modules/PalSpeciesSelector.vue'
import { paldeckForRow } from '@/components/modules/pal-species-selector'
import { canToggleBossVariant, filterPalSkins, usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()

function filterInvalid(list) {
  return list.filter(item => {
    if (palStore.HIDE_INVALID_OPTIONS) {
      return item.InternalName === palStore.SELECTED_PAL_DATA?.CharacterID || !(item.Invalid || item.IsHuman)
    }
    return true
  })
}

const currentSkillIds = () => [
  ...(palStore.SELECTED_PAL_DATA.EquipWaza || []),
  ...(palStore.SELECTED_PAL_DATA.MasteredWaza || []),
];

const activeSkillOptions = () => palStore.filterSkillOptions(
  palStore.ACTIVE_SKILLS_LIST,
  currentSkillIds(),
  palStore.HIDE_INVALID_OPTIONS,
);

const isMaxSuit = key => {
  return palStore.SELECTED_PAL_DATA.Suitabilities[key] >= palStore.MAX_SUITABILITY_LEVEL;
};

const isMinSuit = key => {
  return palStore.SELECTED_PAL_DATA.Suitabilities[key] <=
    (palStore.SELECTED_PAL_DATA.SuitabilityMinimums[key] || 0);
};

const availableSkins = () => filterPalSkins(
  palStore.SKIN_DATA_LIST,
  palStore.SELECTED_PAL_DATA,
  palStore.HIDE_INVALID_OPTIONS,
);

const isMaxLv = () => {
  return palStore.SELECTED_PAL_DATA.Level >= (palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL);
};

const isMinLv = () => {
  return palStore.SELECTED_PAL_DATA.Level <= 1;
};

const isMaxFriendshipLv = () => {
  return palStore.SELECTED_PAL_DATA.FriendshipLevel >= palStore.MAX_FRIENDSHIP_LEVEL;
};

const isMinFriendshipLv = () => {
  return palStore.SELECTED_PAL_DATA.FriendshipLevel <= -3;
};

const suitabilityIconSrc = key => {
  return key ? `/image/suitabilities/${key.split("::").pop()}` : '';
};

const currentPaldeck = () => paldeckForRow(
  palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG],
);

</script>

<template>
  <div :class="['PalEditor', { 'unref': palStore.SELECTED_PAL_DATA.Is_Unref_Pal }]">
    <section
      data-testid="pal-basic-info"
      :class="['pal-basic-info editor-surface', { 'is-unreferenced': palStore.SELECTED_PAL_DATA.Is_Unref_Pal }]"
    >
      <header class="editor-summary">
        <img class="pal-basic-avatar" :src="`/image/pals/${palStore.SELECTED_PAL_DATA.IconAccessKey}`"
          :alt="palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG]?.I18n || palStore.SELECTED_PAL_DATA.DataAccessKeyOG">
        <div class="editor-summary__identity">
          <span class="editor-summary__eyebrow">
            {{ currentPaldeck() ? `PAL ${currentPaldeck()}` : palStore.getTranslatedText("Editor_Basic_Info") }}
          </span>
          <h2 class="editor-summary__title" :title="palStore.SELECTED_PAL_DATA.InternalName">
            {{ palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG]?.I18n ||
              palStore.SELECTED_PAL_DATA.DataAccessKeyOG }}
          </h2>
          <code class="editor-summary__meta">{{ palStore.SELECTED_PAL_DATA.InternalName }}</code>
          <div class="pal-basic-tags">
            <span class="editor-tag">{{ palStore.displayPalElement(palStore.SELECTED_PAL_DATA.DataAccessKeyOG) }}</span>
            <span class="editor-tag" v-if="palStore.SELECTED_PAL_DATA.Level">Lv. {{ palStore.SELECTED_PAL_DATA.Level }}</span>
            <span class="editor-tag"
              v-if="!palStore.SELECTED_PAL_DATA.IsHuman && palStore.SELECTED_PAL_DATA.displaySpecialType() !== 'N/A'">
              {{ palStore.SELECTED_PAL_DATA.displaySpecialType() }}
            </span>
          </div>
          <p class="pal-basic-note" v-if="palStore.SELECTED_PAL_DATA.Is_Unref_Pal">
            {{ palStore.getTranslatedText("Editor_Note_Ghost_Pal") }}
          </p>
        </div>
        <div class="editor-summary__actions">
          <button id="dupe_btn" class="editor-button editor-button--secondary" @click="palStore.dupePal"
            :disabled="palStore.LOADING_FLAG" v-if="!palStore.BASE_PAL_BTN_CLK_FLAG">
            {{ palStore.getTranslatedText("Editor_Btn_Dupe_Pal") }}
          </button>
          <button id="dump_btn" class="editor-button editor-button--secondary" @click="palStore.dumpPalData"
            :disabled="palStore.LOADING_FLAG">
            {{ palStore.getTranslatedText("Editor_Btn_Export_Data") }}
          </button>
          <button id="del_btn" class="editor-button editor-button--danger" @click="palStore.delPal"
            :disabled="palStore.LOADING_FLAG">
            🗑️ {{ palStore.getTranslatedText("Editor_Btn_Delete_Pal") }}
          </button>
        </div>
      </header>

      <section class="editor-section">
        <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Basic_Info") }}</h3>
        <div class="editor-field">
          <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Species") }}</span>
          <div class="editor-field__control">
            <PalSpeciesSelector
              v-model="palStore.SELECTED_PAL_DATA.SelectionKey"
              :rows="palStore.PAL_STATIC_DATA_LIST"
              :hide-invalid="palStore.HIDE_INVALID_OPTIONS"
              :locale="palStore.I18n"
              :disabled="palStore.LOADING_FLAG"
              @apply="palStore.SELECTED_PAL_DATA.changeSpecie"
            />
          </div>
        </div>
      </section>

      <div class="pal-basic-grid">
        <section class="editor-section">
          <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Identity_Appearance") }}</h3>
          <div class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Nickname") }}</span>
            <input class="editor-control" type="text" name="NickName" v-model="palStore.SELECTED_PAL_DATA.NickName"
              :placeholder="palStore.SELECTED_PAL_DATA.I18nName">
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon" @click="palStore.updatePal"
                name="NickName" :value="palStore.SELECTED_PAL_DATA.NickName"
                :aria-label="palStore.getTranslatedText('Editor_Nickname')"
                :disabled="palStore.LOADING_FLAG">✅</button>
            </div>
          </div>
          <div class="editor-field" v-if="availableSkins().length || palStore.SELECTED_PAL_DATA.SkinName">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Skin") }}</span>
            <select class="editor-control" name="SkinName" v-model="palStore.SELECTED_PAL_DATA.SkinName">
              <option value="">{{ palStore.getTranslatedText("Editor_Skin_Default") }}</option>
              <option v-for="skin in availableSkins()" :key="skin.SkinName" :value="skin.SkinName">
                {{ skin.SkinName }}
              </option>
            </select>
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon" @click="palStore.updatePal"
                name="SkinName" :aria-label="palStore.getTranslatedText('Editor_Skin')"
                :value="palStore.SELECTED_PAL_DATA.SkinName" :disabled="palStore.LOADING_FLAG">✅</button>
            </div>
          </div>
          <div class="editor-field" v-if="palStore.SELECTED_PAL_DATA.Gender || !palStore.HIDE_INVALID_OPTIONS">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Gender") }}</span>
            <span class="editor-tag">{{ palStore.SELECTED_PAL_DATA.displayGender() }}</span>
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon"
                @click="palStore.SELECTED_PAL_DATA.swapGender" name="Gender"
                :aria-label="palStore.getTranslatedText('Editor_Gender')"
                :disabled="palStore.LOADING_FLAG">🔄</button>
            </div>
          </div>
          <div class="editor-field" v-if="!palStore.SELECTED_PAL_DATA.IsHuman">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Variant") }}</span>
            <span class="editor-tag">{{ palStore.SELECTED_PAL_DATA.displaySpecialType() }}</span>
            <div class="editor-field__actions">
              <button class="editor-button editor-button--secondary editor-button--icon"
                @click="palStore.SELECTED_PAL_DATA.swapBoss" name="IsBOSS"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Boss')"
                v-if="canToggleBossVariant(palStore.SELECTED_PAL_DATA)"
                :disabled="palStore.LOADING_FLAG">👑</button>
              <button class="editor-button editor-button--secondary editor-button--icon"
                @click="palStore.SELECTED_PAL_DATA.swapRare" name="IsRarePal"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Rare')"
                v-if="canToggleBossVariant(palStore.SELECTED_PAL_DATA)"
                :disabled="palStore.LOADING_FLAG">✨</button>
            </div>
          </div>
        </section>

        <section class="editor-section">
          <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Growth") }}</h3>
          <div class="editor-stepper">
            <div>
              <span class="editor-field__label">💙 {{ palStore.getTranslatedText("Editor_Friendship_Level") }}</span>
              <strong class="editor-stepper__value">{{ palStore.SELECTED_PAL_DATA.FriendshipLevel }}</strong>
            </div>
            <div class="editor-stepper__actions">
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.friendshipLevelDown"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Decrease')"
                :disabled="palStore.LOADING_FLAG || isMinFriendshipLv()">🔽</button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.friendshipLevelUp"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Increase')"
                :disabled="palStore.LOADING_FLAG || isMaxFriendshipLv()">🔼</button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.maxFriendshipLevel"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Max')"
                :disabled="palStore.LOADING_FLAG || isMaxFriendshipLv()">🔝</button>
            </div>
          </div>
          <div class="editor-stepper" v-if="palStore.SELECTED_PAL_DATA.Level">
            <div>
              <span class="editor-field__label">Lv.</span>
              <strong class="editor-stepper__value">{{ palStore.SELECTED_PAL_DATA.Level }}</strong>
            </div>
            <div class="editor-stepper__actions">
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.levelDown"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Decrease')"
                :disabled="palStore.LOADING_FLAG || isMinLv()">🔽</button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.levelUp"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Increase')"
                :disabled="palStore.LOADING_FLAG || isMaxLv()">🔼</button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.maxLevel"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Max')"
                :disabled="palStore.LOADING_FLAG || isMaxLv()">🔝</button>
            </div>
          </div>
          <div class="editor-stat-grid">
            <div class="editor-stat"><span class="editor-stat__label">❤️ {{ palStore.getTranslatedText("Editor_Estimated_HP") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedMaxHP / 1000 }}</strong></div>
            <div class="editor-stat"><span class="editor-stat__label">⚔️ {{ palStore.getTranslatedText("Editor_Estimated_ATK") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedAttack }}</strong></div>
            <div class="editor-stat"><span class="editor-stat__label">🛡️ {{ palStore.getTranslatedText("Editor_Estimated_DEF") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedDefense }}</strong></div>
            <div class="editor-stat"><span class="editor-stat__label">🔨 {{ palStore.getTranslatedText("Editor_Estimated_WorkSpeed") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedCraftSpeed }}</strong></div>
          </div>
        </section>
      </div>

      <details class="editor-disclosure">
        <summary>{{ palStore.getTranslatedText("Editor_Save_Details") }}</summary>
        <div class="pal-technical-grid">
          <div><span class="editor-disclosure__label">🪪 {{ palStore.getTranslatedText("Editor_Pal_CharacterID") }}</span><code>{{ palStore.SELECTED_PAL_DATA.CharacterID }}</code></div>
          <div><span class="editor-disclosure__label">🆔 {{ palStore.getTranslatedText("Editor_Pal_ID") }}</span><code>{{ palStore.SELECTED_PAL_ID }}</code></div>
          <div><span class="editor-disclosure__label">🏘️ {{ palStore.getTranslatedText("Editor_Pal_Guild_ID") }}</span><code>{{ palStore.SELECTED_PAL_DATA.group_id }}</code></div>
          <div class="pal-technical-slot">
            <span class="editor-disclosure__label">📦 {{ palStore.getTranslatedText("Editor_Pal_Slot") }}</span>
            <code :class="{ 'is-out-of-container': !palStore.SELECTED_PAL_DATA.in_owner_palbox }"
              :title="palStore.SELECTED_PAL_DATA.in_owner_palbox ? '' : 'Pal is out of owner palbox, i.e. in viewing cage or taken by someone.'">
              {{ palStore.SELECTED_PAL_DATA.ContainerId }} @ {{ palStore.SELECTED_PAL_DATA.SlotIndex }}
            </code>
            <button class="editor-button editor-button--primary" @click="palStore.updatePal" name="in_owner_palbox"
              :disabled="palStore.LOADING_FLAG" v-if="!palStore.SELECTED_PAL_DATA.in_owner_palbox">
              {{ palStore.getTranslatedText("Editor_Btn_Retrieve_Pal") }}
            </button>
          </div>
          <div><span class="editor-disclosure__label">🗿 {{ palStore.getTranslatedText("Editor_Pal_Owner") }}</span><span>{{ palStore.SELECTED_PAL_DATA.OwnerName || palStore.getTranslatedText("Editor_Pal_No_Owner") }}</span></div>
        </div>
      </details>

      <div class="pal-health-actions" v-if="palStore.SELECTED_PAL_DATA.HasWorkerSick || palStore.SELECTED_PAL_DATA.IsFaintedPal">
        <button class="editor-button editor-button--primary" v-if="palStore.SELECTED_PAL_DATA.HasWorkerSick"
          @click="palStore.updatePal" name="HasWorkerSick" :disabled="palStore.LOADING_FLAG">
          💊 {{ palStore.getTranslatedText("Editor_Btn_Heal_Pal") }}
        </button>
        <button class="editor-button editor-button--primary" v-if="palStore.SELECTED_PAL_DATA.IsFaintedPal"
          @click="palStore.updatePal" name="IsFaintedPal" :disabled="palStore.LOADING_FLAG">
          💉 {{ palStore.getTranslatedText("Editor_Btn_Revive_Pal") }}
        </button>
      </div>
    </section>
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
      <div class="editField spaceBetween" v-if="!palStore.SELECTED_PAL_DATA.IsHuman">
        <p class="const">
          💎 {{ palStore.getTranslatedText("Editor_Awakening") }}
          {{ palStore.SELECTED_PAL_DATA.IsAwakening ? palStore.getTranslatedText("Editor_Awakened") : "-" }}
        </p>
        <button class="edit" @click="palStore.SELECTED_PAL_DATA.toggleAwakening" name="IsAwakening"
          :disabled="palStore.LOADING_FLAG">🔄</button>
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
            v-show="palStore.HIDE_INVALID_OPTIONS || key != 'EPalWorkSuitability::OilExtraction'">
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
                  {{ palStore.skillBadgeText(palStore.ACTIVE_SKILLS[skill]) }}
                </p>
                <p class="skill-warning" v-if="palStore.ACTIVE_SKILLS[skill]?.Assignable === false">
                  {{ palStore.getTranslatedText("Message_Skill_Not_Assignable") }}
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
                  {{ palStore.skillBadgeText(palStore.ACTIVE_SKILLS[skill]) }}
                </p>
                <p class="skill-warning" v-if="palStore.ACTIVE_SKILLS[skill]?.Assignable === false">
                  {{ palStore.getTranslatedText("Message_Skill_Not_Assignable") }}
                </p>
              </span>
            </div>
            <button v-if="!palStore.SELECTED_PAL_DATA.isEquippedSkill(skill)
              && (!palStore.SELECTED_PAL_DATA.isEquipSkillFull() || !palStore.HIDE_INVALID_OPTIONS)" class="edit"
              @click="palStore.SELECTED_PAL_DATA.add_EquipWaza" :name="skill"
              :title="palStore.ACTIVE_SKILLS[skill]?.Assignable === false ? palStore.getTranslatedText('Message_Skill_Not_Assignable') : ''"
              :disabled="palStore.LOADING_FLAG || palStore.ACTIVE_SKILLS[skill]?.Assignable === false">🔼</button>
            <button class="edit del" @click="palStore.SELECTED_PAL_DATA.pop_MasteredWaza" :name="skill"
              :disabled="palStore.LOADING_FLAG">❌</button>
          </div>
          <div class="editField">
            <select class="selector" name="add_MasteredWaza" v-model="palStore.PAL_ACTIVE_SELECTED_ITEM">
              <option value="" key="">
                {{ palStore.getTranslatedText("Editor_Select_Skill") }}
              </option>
              <option v-for="skill in activeSkillOptions()" :value="skill.InternalName"
                :key="skill.InternalName"
                :disabled="skill.Assignable === false"
                :title="skill.Assignable === false ? palStore.getTranslatedText('Message_Skill_Not_Assignable') : skill.I18n[1]">
                {{ `${palStore.displayElement(skill.Element)} ${skill.I18n[0]} ${palStore.skillBadgeText(skill)}
                -
                ⚔️ ${skill.Power} - ⏱️ ${skill.CT}${palStore.HIDE_INVALID_OPTIONS ? '' : ` | ${skill.InternalName}`}` }}
              </option>
            </select>
            <button class="edit" @click="palStore.SELECTED_PAL_DATA.add_MasteredWaza" name="add_MasteredWaza"
              :disabled="palStore.LOADING_FLAG
                || palStore.SELECTED_PAL_DATA.isMasteredSkill(palStore.PAL_ACTIVE_SELECTED_ITEM)
                || palStore.ACTIVE_SKILLS[palStore.PAL_ACTIVE_SELECTED_ITEM]?.Assignable === false">➕</button>
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

.pal-basic-info {
  max-width: 100%;
  flex: 1 1 62rem;
  container-name: pal-basic-info;
  container-type: inline-size;
}

.pal-basic-info.is-unreferenced {
  filter: grayscale(100%);
}

.pal-basic-avatar {
  width: 5.5rem;
  height: 5.5rem;
  object-fit: contain;
  border-radius: 50%;
  background: var(--editor-color-surface-subtle);
}

.pal-basic-tags,
.pal-health-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--editor-space-2);
}

.pal-basic-note {
  margin: 0;
  color: var(--editor-color-muted);
  font-size: .82rem;
}

.pal-basic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 1.75rem;
  min-width: 0;
}

.pal-technical-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--editor-space-3) var(--editor-space-5);
  min-width: 0;
}

.pal-technical-grid > div {
  display: grid;
  gap: var(--editor-space-1);
  min-width: 0;
}

.pal-technical-grid code,
.pal-technical-grid span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.pal-technical-slot {
  grid-template-columns: minmax(0, 1fr) auto;
}

.pal-technical-slot > .editor-disclosure__label {
  grid-column: 1 / -1;
}

.is-out-of-container {
  color: #58c779;
}

@container pal-basic-info (max-width: 720px) {
  .editor-summary {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .editor-summary__actions {
    grid-column: 1 / -1;
    width: 100%;
  }

  .editor-summary__actions .editor-button {
    flex: 1;
  }

  .pal-basic-grid,
  .pal-technical-grid {
    grid-template-columns: 1fr;
  }

  .editor-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container pal-basic-info (max-width: 420px) {
  .editor-summary,
  .editor-stat-grid,
  .editor-stepper {
    grid-template-columns: 1fr;
  }

  .editor-summary__actions {
    width: 100%;
  }

  .editor-summary__actions .editor-button {
    flex: 1;
  }

  .editor-field {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .editor-field__label {
    grid-column: 1 / -1;
  }
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

.PalEditor > div,
.PalEditor > div div {
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
  min-height: 1.8rem;
  margin: .2rem;
  padding: .2rem .4rem;
  border-radius: .5rem;
  color: rgb(208, 212, 226);
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
  overflow-wrap: anywhere;
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

.skill-warning {
  color: #ffd27a;
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
