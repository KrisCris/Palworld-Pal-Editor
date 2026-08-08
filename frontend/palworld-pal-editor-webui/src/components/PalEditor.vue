<script setup>
import { ref } from 'vue'

import PalPortrait from '@/components/modules/PalPortrait.vue'
import PalSpeciesSelector from '@/components/modules/PalSpeciesSelector.vue'
import SearchSelect from '@/components/modules/SearchSelect.vue'
import SegmentedRange from '@/components/modules/SegmentedRange.vue'
import SkillTemplateDialog from '@/components/SkillTemplateDialog.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { paldeckForRow } from '@/components/modules/pal-species-selector'
import { canToggleBossVariant, filterPalSkins, usePalEditorStore } from '@/stores/paleditor'
const palStore = usePalEditorStore()
const updateRange = (name, value) => palStore.updatePal({ target: { name, value } })
const skillTemplateType = ref('')
const openSkillTemplates = type => { skillTemplateType.value = type }

const currentSkillIds = () => [
  ...(palStore.SELECTED_PAL_DATA.EquipWaza || []),
  ...(palStore.SELECTED_PAL_DATA.MasteredWaza || []),
];

const activeSkillOptions = () => palStore.filterSkillOptions(
  palStore.ACTIVE_SKILLS_LIST,
  currentSkillIds(),
  palStore.HIDE_INVALID_OPTIONS,
  palStore.SELECTED_PAL_DATA.IsHuman,
);

const canAssignActiveSkill = skill => palStore.isSkillAssignable(
  skill,
  palStore.SELECTED_PAL_DATA.IsHuman,
);

const canSelectActiveSkill = skill => (
  !palStore.HIDE_INVALID_OPTIONS || canAssignActiveSkill(skill)
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
  return key ? palStore.backendAssetUrl(`/image/suitabilities/${key.split("::").pop()}`) : '';
};

const currentPaldeck = () => paldeckForRow(
  palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG],
);

const skinOptions = () => [
  {
    value: '',
    label: palStore.getTranslatedText('Editor_Skin_Default'),
    icon: palStore.backendAssetUrl(`/image/pals/${palStore.SELECTED_PAL_DATA.IconKey || 'unknown'}`),
  },
  ...availableSkins().map(skin => ({
    value: skin.SkinName,
    label: skin.SkinName,
    icon: palStore.backendAssetUrl(skin.Invalid
      ? '/image/pals/unknown'
      : `/image/pals/skin-${skin.SkinName}`),
  })),
]

const passiveSkillOptions = () => palStore.PASSIVE_SKILLS_LIST.map(skill => ({
  value: skill.InternalName,
  label: skill.I18n[0],
  description: skill.I18n[1],
  meta: skill.InternalName,
  tone: palStore.passiveTier(skill.Rating),
}))

const activeSkillSelectOptions = () => activeSkillOptions().map(skill => {
  const element = palStore.elementIconKey(skill.Element)
  return {
    value: skill.InternalName,
    label: skill.I18n[0],
    description: `${skillBadgeLabels(skill)} · ${palStore.getTranslatedText('Editor_Skill_ATK')} ${skill.Power} · ${palStore.getTranslatedText('Editor_Skill_CD')} ${skill.CT}`,
    tooltip: skill.I18n[1],
    meta: `${skill.InternalName} ${skill.Element}`,
    disabled: !canSelectActiveSkill(skill),
    icon: element ? palStore.backendAssetUrl(`/image/elements/Element_${element}`) : '',
  }
})

const specialTypeLabel = key => palStore.getTranslatedText(`Editor_Variant_${key}`);
const skillBadgeLabels = skill => palStore.skillBadges(
  skill,
  palStore.SELECTED_PAL_DATA.IsHuman,
)
  .map(badge => {
    const label = palStore.getTranslatedText(palStore.skillBadgeTranslationKey(badge))
    return badge === 'exclusive' && skill.LearnerNames?.length
      ? `${skill.LearnerNames.join(' / ')} · ${label}`
      : label
  })
  .join(' · ');

const portraitBorder = pal => pal.IsAwakening
  ? 'var(--editor-color-awakened)'
  : pal.IsBOSS
  ? 'var(--editor-color-danger)'
  : pal.IsRarePal ? 'var(--editor-color-lucky)' : 'var(--editor-color-border)'

</script>

<template>
  <div class="pal-editor" :class="{ 'is-unreferenced': palStore.SELECTED_PAL_DATA.Is_Unref_Pal }">
    <section
      data-testid="pal-basic-info"
      :class="['pal-basic-info editor-surface', { 'is-unreferenced': palStore.SELECTED_PAL_DATA.Is_Unref_Pal }]"
    >
      <header class="editor-summary">
        <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${palStore.SELECTED_PAL_DATA.IconAccessKey}`)"
          :alt="palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKeyOG]?.I18n || palStore.SELECTED_PAL_DATA.DataAccessKeyOG"
          size="5.5rem" :border-color="portraitBorder(palStore.SELECTED_PAL_DATA)"
          :glow-color="palStore.SELECTED_PAL_DATA.IsAwakening ? 'var(--editor-color-awakened)' : ''">
          <template #top-left>
            <img v-if="palStore.SELECTED_PAL_DATA.IsBOSS" :src="palStore.backendAssetUrl('/image/ui/boss')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-else-if="palStore.SELECTED_PAL_DATA.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #top-right>
            <img v-if="palStore.SELECTED_PAL_DATA.FavoriteIndex > 0" class="game-priority-icon"
              :src="palStore.backendAssetUrl(`/image/ui/priority-${palStore.SELECTED_PAL_DATA.FavoriteIndex}`)" alt=""
              @error="$event.currentTarget.hidden = true">
            <img v-else-if="palStore.SELECTED_PAL_DATA.IsBOSS && palStore.SELECTED_PAL_DATA.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #bottom-left>
            <img v-if="palStore.SELECTED_PAL_DATA.FavoriteIndex > 0 && palStore.SELECTED_PAL_DATA.IsBOSS && palStore.SELECTED_PAL_DATA.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-if="palStore.SELECTED_PAL_DATA.IsImportedCharacter" class="game-dna-icon"
              :src="palStore.backendAssetUrl('/image/ui/dna')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
        </PalPortrait>
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
            <span class="editor-tag" v-if="palStore.palElementKeys(palStore.SELECTED_PAL_DATA.DataAccessKeyOG).length">
              <img v-for="element in palStore.palElementKeys(palStore.SELECTED_PAL_DATA.DataAccessKeyOG)"
                :key="element" class="element-icon" :src="palStore.backendAssetUrl(`/image/elements/Element_${element}`)" :alt="element">
            </span>
            <span class="editor-tag" v-if="palStore.SELECTED_PAL_DATA.Level">Lv. {{ palStore.SELECTED_PAL_DATA.Level }}</span>
            <span class="editor-tag"
              v-if="!palStore.SELECTED_PAL_DATA.IsHuman && palStore.specialTypeKeys(palStore.SELECTED_PAL_DATA).length">
              {{ palStore.specialTypeKeys(palStore.SELECTED_PAL_DATA).map(specialTypeLabel).join(' · ') }}
            </span>
          </div>
          <p class="pal-basic-note" v-if="palStore.SELECTED_PAL_DATA.Is_Unref_Pal">
            {{ palStore.getTranslatedText("Editor_Note_Ghost_Pal") }}
          </p>
        </div>
        <div class="editor-summary__actions">
          <button id="maximize_pal_btn" class="editor-button editor-button--primary" @click="palStore.maximizePal"
            :disabled="palStore.LOADING_FLAG">
            <UiIcon name="maximum" /> {{ palStore.getTranslatedText("Editor_Btn_Maximize_Pal") }}
          </button>
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
            <UiIcon name="delete" /> {{ palStore.getTranslatedText("Editor_Btn_Delete_Pal") }}
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
                :disabled="palStore.LOADING_FLAG"><UiIcon name="check" /></button>
            </div>
          </div>
          <div class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_ImportedCharacter") }}</span>
            <span class="editor-tag">
              <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/dna')" alt="">
              <UiIcon v-if="palStore.SELECTED_PAL_DATA.IsImportedCharacter" name="check" />
              <template v-else>-</template>
            </span>
            <div class="editor-field__actions">
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': palStore.SELECTED_PAL_DATA.IsImportedCharacter }]"
                name="IsImportedCharacter"
                :aria-label="palStore.getTranslatedText('Editor_ImportedCharacter')"
                :aria-pressed="palStore.SELECTED_PAL_DATA.IsImportedCharacter"
                :disabled="palStore.LOADING_FLAG"
                @click="updateRange('IsImportedCharacter', !palStore.SELECTED_PAL_DATA.IsImportedCharacter)">
                <UiIcon name="refresh" />
              </button>
            </div>
          </div>
          <div class="editor-field" v-if="availableSkins().length || palStore.SELECTED_PAL_DATA.SkinName">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Skin") }}</span>
            <SearchSelect v-model="palStore.SELECTED_PAL_DATA.SkinName"
              :options="skinOptions()" :placeholder="palStore.getTranslatedText('Editor_Skin_Default')"
              :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
              :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
              :aria-label="palStore.getTranslatedText('Editor_Skin')" :disabled="palStore.LOADING_FLAG" />
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon" @click="palStore.updatePal"
                name="SkinName" :aria-label="palStore.getTranslatedText('Editor_Skin')"
                :value="palStore.SELECTED_PAL_DATA.SkinName" :disabled="palStore.LOADING_FLAG"><UiIcon name="check" /></button>
            </div>
          </div>
          <div class="editor-field" v-if="palStore.SELECTED_PAL_DATA.Gender || !palStore.HIDE_INVALID_OPTIONS">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Gender") }}</span>
            <span class="editor-tag" v-if="palStore.genderKey(palStore.SELECTED_PAL_DATA.Gender)">
              <img class="game-icon" :src="palStore.backendAssetUrl(`/image/ui/gender-${palStore.genderKey(palStore.SELECTED_PAL_DATA.Gender)}`)" alt="">
            </span>
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon"
                @click="palStore.SELECTED_PAL_DATA.swapGender" name="Gender"
                :aria-label="palStore.getTranslatedText('Editor_Gender')"
                :disabled="palStore.LOADING_FLAG"><UiIcon name="refresh" /></button>
            </div>
          </div>
          <div class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("PalList_Sort_Priority") }}</span>
            <div class="pal-priority-control" role="group" :aria-label="palStore.getTranslatedText('PalList_Sort_Priority')">
              <button v-for="priority in [0, 1, 2, 3]" :key="priority" type="button"
                :class="['editor-button', palStore.SELECTED_PAL_DATA.FavoriteIndex === priority ? 'editor-button--primary' : 'editor-button--secondary']"
                :aria-label="`${palStore.getTranslatedText('PalList_Sort_Priority')}: ${['—', 'I', 'II', 'III'][priority]}`"
                :aria-pressed="palStore.SELECTED_PAL_DATA.FavoriteIndex === priority"
                :disabled="palStore.LOADING_FLAG"
                @click="updateRange('FavoriteIndex', priority)">
                <span v-if="priority === 0">—</span>
                <img v-else class="game-priority-icon"
                  :src="palStore.backendAssetUrl(`/image/ui/priority-${priority}`)"
                  :alt="['—', 'I', 'II', 'III'][priority]">
              </button>
            </div>
          </div>
          <div class="editor-field" v-if="!palStore.SELECTED_PAL_DATA.IsHuman">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Variant") }}</span>
            <span class="editor-tag">
              {{ palStore.specialTypeKeys(palStore.SELECTED_PAL_DATA).map(specialTypeLabel).join(' · ') || '-' }}
            </span>
            <div class="editor-field__actions">
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': palStore.SELECTED_PAL_DATA.IsBOSS }]"
                @click="palStore.SELECTED_PAL_DATA.swapBoss" name="IsBOSS"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Boss')"
                :aria-pressed="palStore.SELECTED_PAL_DATA.IsBOSS"
                v-if="canToggleBossVariant(palStore.SELECTED_PAL_DATA)"
                :disabled="palStore.LOADING_FLAG"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/boss')" alt=""></button>
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': palStore.SELECTED_PAL_DATA.IsRarePal }]"
                @click="palStore.SELECTED_PAL_DATA.swapRare" name="IsRarePal"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Rare')"
                :aria-pressed="palStore.SELECTED_PAL_DATA.IsRarePal"
                v-if="canToggleBossVariant(palStore.SELECTED_PAL_DATA)"
                :disabled="palStore.LOADING_FLAG"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/rare')" alt=""></button>
            </div>
          </div>
        </section>

        <section class="editor-section">
          <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Growth") }}</h3>
          <div class="editor-stepper">
            <div>
              <span class="editor-field__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/friendship')" alt=""> {{ palStore.getTranslatedText("Editor_Friendship_Level") }}</span>
              <strong class="editor-stepper__value">{{ palStore.SELECTED_PAL_DATA.FriendshipLevel }}</strong>
            </div>
            <div class="editor-stepper__actions">
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.friendshipLevelDown"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Decrease')"
                :disabled="palStore.LOADING_FLAG || isMinFriendshipLv()"><UiIcon name="minus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.friendshipLevelUp"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Increase')"
                :disabled="palStore.LOADING_FLAG || isMaxFriendshipLv()"><UiIcon name="plus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.maxFriendshipLevel"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Max')"
                :disabled="palStore.LOADING_FLAG || isMaxFriendshipLv()"><UiIcon name="maximum" /></button>
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
                :disabled="palStore.LOADING_FLAG || isMinLv()"><UiIcon name="minus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.levelUp"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Increase')"
                :disabled="palStore.LOADING_FLAG || isMaxLv()"><UiIcon name="plus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.maxLevel"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Max')"
                :disabled="palStore.LOADING_FLAG || isMaxLv()"><UiIcon name="maximum" /></button>
            </div>
          </div>
        </section>
      </div>
      <div class="editor-stat-grid">
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-health')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_HP") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedMaxHP / 1000 }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_ATK") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedAttack }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_DEF") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedDefense }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-work-speed')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_WorkSpeed") }}</span><strong class="editor-stat__value">{{ palStore.SELECTED_PAL_DATA.ComputedCraftSpeed }}</strong></div>
      </div>

      <details class="editor-disclosure"
        :open="palStore.PAL_SAVE_DETAILS_OPEN"
        @toggle="palStore.PAL_SAVE_DETAILS_OPEN = $event.currentTarget.open">
        <summary>{{ palStore.getTranslatedText("Editor_Save_Details") }}</summary>
        <div class="pal-technical-grid">
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_CharacterID") }}</span><code>{{ palStore.SELECTED_PAL_DATA.CharacterID }}</code></div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_ID") }}</span><code>{{ palStore.SELECTED_PAL_ID }}</code></div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Guild_ID") }}</span><code>{{ palStore.SELECTED_PAL_DATA.group_id }}</code></div>
          <div class="pal-technical-slot">
            <span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Slot") }}</span>
            <code :class="{ 'is-out-of-container': !palStore.SELECTED_PAL_DATA.in_owner_palbox }"
              :title="palStore.SELECTED_PAL_DATA.in_owner_palbox ? '' : 'Pal is out of owner palbox, i.e. in viewing cage or taken by someone.'">
              {{ palStore.SELECTED_PAL_DATA.ContainerId }} @ {{ palStore.SELECTED_PAL_DATA.SlotIndex }}
            </code>
            <button class="editor-button editor-button--primary" @click="palStore.updatePal" name="in_owner_palbox"
              :disabled="palStore.LOADING_FLAG" v-if="!palStore.SELECTED_PAL_DATA.in_owner_palbox">
              {{ palStore.getTranslatedText("Editor_Btn_Retrieve_Pal") }}
            </button>
          </div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Owner") }}</span><span>{{ palStore.SELECTED_PAL_DATA.OwnerName || palStore.getTranslatedText("Editor_Pal_No_Owner") }}</span></div>
        </div>
      </details>

      <div class="pal-health-actions" v-if="palStore.SELECTED_PAL_DATA.HasWorkerSick || palStore.SELECTED_PAL_DATA.IsFaintedPal">
        <button class="editor-button editor-button--primary" v-if="palStore.SELECTED_PAL_DATA.HasWorkerSick"
          @click="palStore.updatePal" name="HasWorkerSick" :disabled="palStore.LOADING_FLAG">
          <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/heal')" alt=""> {{ palStore.getTranslatedText("Editor_Btn_Heal_Pal") }}
        </button>
        <button class="editor-button editor-button--primary" v-if="palStore.SELECTED_PAL_DATA.IsFaintedPal"
          @click="palStore.updatePal" name="IsFaintedPal" :disabled="palStore.LOADING_FLAG">
          <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/revive')" alt=""> {{ palStore.getTranslatedText("Editor_Btn_Revive_Pal") }}
        </button>
      </div>
    </section>
    <div class="pal-progression-grid">
      <section class="pal-panel editor-surface">
        <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_IV") }}</h2>
        <div class="range-grid">
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-health')" alt=""> {{ palStore.getTranslatedText("Editor_IV_HP") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Talent_HP }}</strong>
            <SegmentedRange name="Talent_HP" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_HP"
              @change="updateRange('Talent_HP', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_IV_DEF") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Talent_Defense }}</strong>
            <SegmentedRange name="Talent_Defense" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_Defense"
              @change="updateRange('Talent_Defense', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_IV_ATK") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Talent_Shot }}</strong>
            <SegmentedRange name="Talent_Shot" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_Shot"
              @change="updateRange('Talent_Shot', $event)" />
          </label>
          <label class="range-control" v-if="!palStore.HIDE_INVALID_OPTIONS">
            <span>{{ palStore.getTranslatedText("Editor_IV_MELEE") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Talent_Melee }}</strong>
            <SegmentedRange name="Talent_Melee" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Talent_Melee"
              @change="updateRange('Talent_Melee', $event)" />
          </label>
        </div>
        <div class="pal-inline-action" v-if="!palStore.SELECTED_PAL_DATA.IsHuman">
          <span>{{ palStore.getTranslatedText("Editor_Awakening") }}</span>
          <strong>{{ palStore.SELECTED_PAL_DATA.IsAwakening ? palStore.getTranslatedText("Editor_Awakened") : "-" }}</strong>
          <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.toggleAwakening"
            name="IsAwakening" :aria-label="palStore.getTranslatedText('Editor_Awakening')"
            :disabled="palStore.LOADING_FLAG"><UiIcon name="refresh" /></button>
        </div>
      </section>

      <section class="pal-panel editor-surface">
        <h2 class="pal-panel__heading"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/soul')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_Upgrade") }}</h2>
        <div class="range-grid">
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-health')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_HP") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Rank_HP }}</strong>
            <SegmentedRange name="Rank_HP" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Rank_HP"
              @change="updateRange('Rank_HP', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_ATK") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Rank_Attack }}</strong>
            <SegmentedRange name="Rank_Attack" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Rank_Attack"
              @change="updateRange('Rank_Attack', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_DEF") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Rank_Defence }}</strong>
            <SegmentedRange name="Rank_Defence" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Rank_Defence"
              @change="updateRange('Rank_Defence', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-work-speed')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_CraftSpeed") }}</span>
            <strong>{{ palStore.SELECTED_PAL_DATA.Rank_CraftSpeed }}</strong>
            <SegmentedRange name="Rank_CraftSpeed" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255"
              :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Rank_CraftSpeed"
              @change="updateRange('Rank_CraftSpeed', $event)" />
          </label>
        </div>
        <h3 class="pal-panel__subheading"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/condense')" alt=""> {{ palStore.getTranslatedText("Editor_Condenser") }}</h3>
        <label class="range-control range-control--wide">
          <span>{{ palStore.getTranslatedText("Editor_Condenser_Rank") }}</span>
          <strong>{{ palStore.SELECTED_PAL_DATA.Rank - 1 }}</strong>
          <SegmentedRange name="Rank" :min="1" :max="palStore.HIDE_INVALID_OPTIONS ? 5 : 255"
            :disabled="palStore.LOADING_FLAG" v-model="palStore.SELECTED_PAL_DATA.Rank"
            @change="updateRange('Rank', $event)" />
        </label>
      </section>
    </div>

    <section class="pal-panel editor-surface"
      v-if="palStore.PAL_STATIC_DATA[palStore.SELECTED_PAL_DATA.DataAccessKey]?.Suitabilities">
      <div class="pal-panel__header">
        <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Suitabilities") }}</h2>
        <button class="editor-button editor-button--primary" type="button"
          @click="palStore.SELECTED_PAL_DATA.maxSuitabilities"
          :disabled="palStore.LOADING_FLAG">
          <UiIcon name="maximum" /> {{ palStore.getTranslatedText("Editor_Suitabilities_Max") }}
        </button>
      </div>
      <div class="suitability-grid">
        <div class="suitability-control" v-for="(value, key) in palStore.SELECTED_PAL_DATA.Suitabilities" :key="key"
          v-show="palStore.HIDE_INVALID_OPTIONS || key != 'EPalWorkSuitability::OilExtraction'">
          <img class="suitability-icon" :src="suitabilityIconSrc(key)" :alt="key.split('::').pop()" :title="key.split('::').pop()">
          <strong>{{ value }}</strong>
          <div class="suitability-control__actions">
            <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.suitDown" :name="key"
              :aria-label="`${key} -`" :disabled="palStore.LOADING_FLAG || isMinSuit(key)"><UiIcon name="minus" /></button>
            <button class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.suitUp" :name="key"
              :aria-label="`${key} +`" :disabled="palStore.LOADING_FLAG || isMaxSuit(key)"><UiIcon name="plus" /></button>
          </div>
        </div>
      </div>
    </section>

    <section class="pal-panel editor-surface">
      <div class="skill-section">
        <div class="skill-section__header">
          <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Passive_Skills") }}</h2>
          <button class="editor-button editor-button--secondary" type="button" @click="openSkillTemplates('passive')">
            <UiIcon name="copy" /> {{ palStore.getTranslatedText('SkillTemplate_Button') }}
          </button>
        </div>
        <div class="skill-cards">
          <article class="skill-card" v-for="skill in palStore.SELECTED_PAL_DATA.PassiveSkillList" :key="skill"
            :title="palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill">
            <span :class="['passive-tier', `passive-tier--${palStore.passiveTier(palStore.PASSIVE_SKILLS[skill]?.Rating)}`]" aria-hidden="true"></span>
            <div class="skill-card__identity">
              <strong>{{ palStore.PASSIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
              <small>{{ palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill }}</small>
            </div>
            <button class="editor-button editor-button--icon editor-button--danger"
              @click="palStore.SELECTED_PAL_DATA.pop_PassiveSkillList" :name="skill"
              :aria-label="`${palStore.getTranslatedText('Editor_Passive_Skills')} - ${skill}`"
              :disabled="palStore.LOADING_FLAG"><UiIcon name="close" /></button>
          </article>
        </div>
        <div class="skill-add" v-if="!palStore.HIDE_INVALID_OPTIONS || palStore.SELECTED_PAL_DATA.PassiveSkillList.length < 4">
          <SearchSelect v-model="palStore.PAL_PASSIVE_SELECTED_ITEM" placement="top"
            :options="passiveSkillOptions()" :placeholder="palStore.getTranslatedText('Editor_Select_Skill')"
            :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
            :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
            :aria-label="palStore.getTranslatedText('Editor_Passive_Skills')" :disabled="palStore.LOADING_FLAG" />
          <button class="editor-button editor-button--icon editor-button--primary"
            @click="palStore.SELECTED_PAL_DATA.add_PassiveSkillList" name="add_PassiveSkillList"
            :aria-label="palStore.getTranslatedText('Editor_Passive_Skills')"
            :disabled="palStore.LOADING_FLAG || palStore.SELECTED_PAL_DATA.isEquippedPassiveSkill(palStore.PAL_PASSIVE_SELECTED_ITEM)"><UiIcon name="plus" /></button>
        </div>
      </div>

      <div class="skill-section">
        <div class="skill-section__header">
          <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Equipped_Skills") }}</h2>
          <button class="editor-button editor-button--secondary" type="button" @click="openSkillTemplates('active')">
            <UiIcon name="copy" /> {{ palStore.getTranslatedText('SkillTemplate_Button') }}
          </button>
        </div>
        <div class="skill-cards">
          <article class="skill-card" v-for="skill in palStore.SELECTED_PAL_DATA.EquipWaza" :key="skill"
            :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">
            <img v-if="palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)" class="element-icon"
              :src="palStore.backendAssetUrl(`/image/elements/Element_${palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)}`)" alt="">
            <div class="skill-card__identity">
              <strong>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
              <small>{{ palStore.getTranslatedText("Editor_Skill_ATK") }} {{ palStore.ACTIVE_SKILLS[skill]?.Power }} · {{ palStore.getTranslatedText("Editor_Skill_CD") }} {{ palStore.ACTIVE_SKILLS[skill]?.CT }} · {{ skillBadgeLabels(palStore.ACTIVE_SKILLS[skill]) }}</small>
              <small class="skill-warning" v-if="!canAssignActiveSkill(palStore.ACTIVE_SKILLS[skill])">{{ palStore.getTranslatedText("Message_Skill_Not_Assignable") }}</small>
            </div>
            <button class="editor-button editor-button--icon editor-button--danger"
              @click="palStore.SELECTED_PAL_DATA.pop_EquipWaza" :name="skill"
              :aria-label="`${palStore.getTranslatedText('Editor_Equipped_Skills')} - ${skill}`"
              :disabled="palStore.LOADING_FLAG"><UiIcon name="close" /></button>
          </article>
        </div>
      </div>

      <div class="skill-section">
        <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Mastered_Skills") }}</h2>
        <div class="skill-cards">
          <article class="skill-card" v-for="skill in palStore.SELECTED_PAL_DATA.MasteredWaza" :key="skill"
            :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">
            <img v-if="palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)" class="element-icon"
              :src="palStore.backendAssetUrl(`/image/elements/Element_${palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)}`)" alt="">
            <div class="skill-card__identity">
              <strong>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
              <small>{{ palStore.getTranslatedText("Editor_Skill_ATK") }} {{ palStore.ACTIVE_SKILLS[skill]?.Power }} · {{ palStore.getTranslatedText("Editor_Skill_CD") }} {{ palStore.ACTIVE_SKILLS[skill]?.CT }} · {{ skillBadgeLabels(palStore.ACTIVE_SKILLS[skill]) }}</small>
              <small class="skill-warning" v-if="!canAssignActiveSkill(palStore.ACTIVE_SKILLS[skill])">{{ palStore.getTranslatedText("Message_Skill_Not_Assignable") }}</small>
            </div>
            <div class="skill-card__actions">
              <button v-if="!palStore.SELECTED_PAL_DATA.isEquippedSkill(skill)
                && (!palStore.SELECTED_PAL_DATA.isEquipSkillFull() || !palStore.HIDE_INVALID_OPTIONS)"
                class="editor-button editor-button--icon" @click="palStore.SELECTED_PAL_DATA.add_EquipWaza" :name="skill"
                :aria-label="`${palStore.getTranslatedText('Editor_Equipped_Skills')} + ${skill}`"
                :title="!canAssignActiveSkill(palStore.ACTIVE_SKILLS[skill]) ? palStore.getTranslatedText('Message_Skill_Not_Assignable') : ''"
                :disabled="palStore.LOADING_FLAG || !canSelectActiveSkill(palStore.ACTIVE_SKILLS[skill])"><UiIcon name="plus" /></button>
              <button class="editor-button editor-button--icon editor-button--danger"
                @click="palStore.SELECTED_PAL_DATA.pop_MasteredWaza" :name="skill"
                :aria-label="`${palStore.getTranslatedText('Editor_Mastered_Skills')} - ${skill}`"
                :disabled="palStore.LOADING_FLAG"><UiIcon name="close" /></button>
            </div>
          </article>
        </div>
        <div class="skill-add">
          <SearchSelect v-model="palStore.PAL_ACTIVE_SELECTED_ITEM" placement="top"
            :options="activeSkillSelectOptions()" :placeholder="palStore.getTranslatedText('Editor_Select_Skill')"
            :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
            :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
            :aria-label="palStore.getTranslatedText('Editor_Mastered_Skills')" :disabled="palStore.LOADING_FLAG" />
          <button class="editor-button editor-button--icon editor-button--primary"
            @click="palStore.SELECTED_PAL_DATA.add_MasteredWaza" name="add_MasteredWaza"
            :aria-label="palStore.getTranslatedText('Editor_Mastered_Skills')"
            :disabled="palStore.LOADING_FLAG
              || palStore.SELECTED_PAL_DATA.isMasteredSkill(palStore.PAL_ACTIVE_SELECTED_ITEM)
              || !canSelectActiveSkill(palStore.ACTIVE_SKILLS[palStore.PAL_ACTIVE_SELECTED_ITEM])"><UiIcon name="plus" /></button>
        </div>
      </div>
    </section>
    <SkillTemplateDialog v-if="skillTemplateType" :type="skillTemplateType" @close="skillTemplateType = ''" />
  </div>
</template>

<style scoped>
.pal-editor {
  display: grid;
  width: 100%;
  min-width: 0;
  gap: var(--editor-space-3);
  container: pal-editor / inline-size;
}

.pal-editor.is-unreferenced {
  filter: grayscale(100%);
}

.pal-basic-info {
  max-width: 100%;
  width: 100%;
  container-name: pal-basic-info;
  container-type: inline-size;
}

.pal-basic-info.is-unreferenced {
  filter: grayscale(100%);
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
  color: var(--editor-color-success);
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

.game-icon,
.element-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 auto;
  object-fit: contain;
}

.editor-button--variant.is-active {
  border-color: var(--editor-color-primary);
  background: color-mix(in srgb, var(--editor-color-primary) 24%, var(--editor-color-surface-raised));
}

.pal-priority-control {
  display: grid;
  grid-template-columns: repeat(4, minmax(2.5rem, 1fr));
  gap: var(--editor-space-1);
}

.pal-priority-control .editor-button {
  min-width: 0;
}

.pal-priority-control .game-priority-icon {
  width: 1.6rem;
  height: 1.6rem;
  object-fit: contain;
}

.passive-tier {
  width: .65rem;
  height: .65rem;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--editor-color-muted);
}

.passive-tier--top { background: var(--editor-color-passive-top); }
.passive-tier--high { background: var(--editor-color-passive-high); }
.passive-tier--positive { background: var(--editor-color-passive-positive); }
.passive-tier--negative { background: var(--editor-color-passive-negative); }

.pal-progression-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--editor-space-3);
  min-width: 0;
}

.pal-panel.editor-surface {
  width: 100%;
  gap: var(--editor-space-3);
  padding: var(--editor-space-4);
  border-radius: var(--editor-radius-md);
}

.pal-panel__heading {
  display: flex;
  align-items: center;
  gap: var(--editor-space-2);
  margin: 0;
  padding-bottom: var(--editor-space-2);
  border-bottom: 1px solid var(--editor-color-border);
  font-size: 1rem;
}

.pal-panel__subheading {
  display: flex;
  align-items: center;
  gap: var(--editor-space-2);
  margin: var(--editor-space-1) 0 0;
  padding-top: var(--editor-space-3);
  border-top: 1px solid var(--editor-color-border);
  font-size: .9rem;
}

.pal-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-3);
  padding-bottom: var(--editor-space-2);
  border-bottom: 1px solid var(--editor-color-border);
}

.pal-panel__header .pal-panel__heading {
  padding-bottom: 0;
  border-bottom: 0;
}

.range-grid,
.suitability-grid,
.skill-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: var(--editor-space-2);
  min-width: 0;
}

.range-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-1) var(--editor-space-2);
  min-width: 0;
  padding: var(--editor-space-2) var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-subtle);
}

.range-control > span {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--editor-space-1);
  color: var(--editor-color-muted);
}

.range-control .segmented-range {
  grid-column: 1 / -1;
  width: 100%;
  accent-color: var(--editor-color-focus);
}

.range-control--wide {
  margin-top: var(--editor-space-1);
}

.pal-inline-action,
.suitability-control,
.skill-add,
.skill-card {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--editor-space-2);
}

.pal-inline-action {
  padding-top: var(--editor-space-2);
  border-top: 1px solid var(--editor-color-border);
}

.pal-inline-action strong,
.skill-card__identity {
  min-width: 0;
  flex: 1;
}

.suitability-control {
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-subtle);
}

.suitability-icon {
  width: 2rem;
  height: 2rem;
  object-fit: contain;
}

.suitability-control__actions,
.skill-card__actions {
  display: flex;
  margin-left: auto;
  gap: var(--editor-space-1);
}

.skill-section {
  display: grid;
  gap: var(--editor-space-2);
  min-width: 0;
}

.skill-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-3);
}

.skill-section + .skill-section {
  padding-top: var(--editor-space-3);
  border-top: 1px solid var(--editor-color-border);
}

.skill-card {
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-subtle);
}

.skill-card__identity {
  display: grid;
  gap: var(--editor-space-1);
  overflow: hidden;
}

.skill-card__identity strong,
.skill-card__identity small {
  overflow: hidden;
  text-overflow: ellipsis;
}

.skill-card__identity small {
  color: var(--editor-color-muted);
}

.skill-add > :first-child {
  min-width: 0;
  flex: 1;
}

.skill-warning {
  color: var(--editor-color-warning) !important;
}

@container pal-editor (max-width: 42rem) {
  .pal-progression-grid {
    grid-template-columns: 1fr;
  }
}

@container pal-editor (max-width: 30rem) {
  .range-grid,
  .suitability-grid,
  .skill-cards {
    grid-template-columns: 1fr;
  }
}
</style>
