<script setup>
import { computed, ref, watch } from 'vue'

import PalContainerMoveDialog from '@/components/PalContainerMoveDialog.vue'
import PalPortrait from '@/components/modules/PalPortrait.vue'
import PalSpeciesSelector from '@/components/modules/PalSpeciesSelector.vue'
import SearchSelect from '@/components/modules/SearchSelect.vue'
import SegmentedRange from '@/components/modules/SegmentedRange.vue'
import { formatContainerLabel } from '@/components/modules/pal-container-label'
import SkillTemplateDialog from '@/components/SkillTemplateDialog.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { canToggleBossVariant, filterPalSkins, usePalEditorStore } from '@/stores/paleditor'
import { usePalsStore } from '@/stores/pals'
const palStore = usePalEditorStore()
const palsStore = usePalsStore()
// The Pal this page edits. It is the object in the Pal cache, so the `v-model`
// bindings below write to the same place the list reads.
const pal = computed(() => palsStore.selectedPal)
const updateRange = (name, value) => palStore.updatePal({ target: { name, value } })
// Which species the selector is offering, which is a control's state and not the
// Pal's: it only becomes the Pal's when the apply button is pressed.
const speciesSelection = ref('')
watch(() => palsStore.selectedRecordKey, () => {
  speciesSelection.value = palStore.PAL_STATIC_DATA[pal.value?.CharacterID]
    ? pal.value.CharacterID
    : pal.value?.DataAccessKey ?? ''
}, { immediate: true })
const skillTemplateType = ref('')
const showMoveDialog = ref(false)
const passiveSkillSelect = ref(null)
const activeSkillSelect = ref(null)
const skinSelect = ref(null)
// A record only keeps a StorageKey while it really occupies the slot it records,
// so a missing one is exactly the location the move dialog cannot work from.
const moveBlocked = computed(() => pal.value.IsExpeditionPal || !pal.value.storageKey)
// A Pal is not a container, but it says which one it is in. This is the label of
// that container, built from the Pal's own account of it.
const externalContainerLabel = computed(() => formatContainerLabel(
  {
    ContainerKind: pal.value.containerKind,
    ContainerLabel: pal.value.containerLabel,
    ContainerId: pal.value.ContainerId,
    OwnerName: pal.value.OwnerName,
  },
  palStore.getTranslatedText,
))
const ownerLabel = computed(() => pal.value.OwnerName
  || (pal.value.storageKind !== 'world'
    ? externalContainerLabel.value
    : palStore.getTranslatedText('Editor_Pal_No_Owner')))
const guildLabel = computed(() => pal.value.groupId
  || (pal.value.storageKind === 'global_palbox'
    ? externalContainerLabel.value
    : ''))
const technicalContainer = computed(() => pal.value.storageKind === 'world'
  ? pal.value.ContainerId
  : externalContainerLabel.value)
const technicalSlot = computed(() => pal.value.SlotIndex)
const openSkillTemplates = type => { skillTemplateType.value = type }

const currentSkillIds = () => [
  ...(pal.value.EquipWaza || []),
  ...(pal.value.MasteredWaza || []),
];

const activeSkillOptions = () => palStore.filterSkillOptions(
  palStore.ACTIVE_SKILLS_LIST,
  currentSkillIds(),
  palStore.HIDE_INVALID_OPTIONS,
  pal.value.IsHuman,
);

const canAssignActiveSkill = skill => palStore.isSkillAssignable(
  skill,
  pal.value.IsHuman,
);

const canSelectActiveSkill = skill => (
  !palStore.HIDE_INVALID_OPTIONS || canAssignActiveSkill(skill)
);

const showEquipMasteredAction = skill => !pal.value.EquipWaza.includes(skill);

const canEquipMasteredSkill = skill => (
  showEquipMasteredAction(skill)
  && canSelectActiveSkill(palStore.ACTIVE_SKILLS[skill])
);

const activeSkillEquipTitle = skill => {
  if (!canSelectActiveSkill(palStore.ACTIVE_SKILLS[skill])) {
    return palStore.getTranslatedText('Message_Skill_Not_Assignable');
  }
  if (isEquipSkillFull()) {
    return palStore.getTranslatedText('Message_Skill_Equip_Full');
  }
  return '';
};

const isEquipSkillFull = () => pal.value.EquipWaza.length >= 3;

const addPassiveSkill = () => {
  palStore.addPassiveSkill();
  passiveSkillSelect.value?.close();
};

const addActiveSkill = () => {
  palStore.addMasteredWaza();
  activeSkillSelect.value?.close();
};

const applySkin = () => {
  palStore.updatePal({ target: { name: 'SkinName', value: pal.value.SkinName } });
  skinSelect.value?.close();
};

const isMaxSuit = key => {
  return pal.value.Suitabilities[key] >= palStore.MAX_SUITABILITY_LEVEL;
};

const isMinSuit = key => {
  return pal.value.Suitabilities[key] <= (pal.value.SuitabilityMinimums[key] || 0);
};

const availableSkins = () => filterPalSkins(
  palStore.SKIN_DATA_LIST,
  pal.value,
  palStore.HIDE_INVALID_OPTIONS,
);

const isMaxLv = () => {
  return pal.value.Level >= (palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_LEVEL : palStore.MAX_INVALID_LEVEL);
};

const isMinLv = () => {
  return pal.value.Level <= 1;
};

const isMaxFriendshipLv = () => {
  return pal.value.FriendshipLevel >= palStore.MAX_FRIENDSHIP_LEVEL;
};

const isMinFriendshipLv = () => {
  return pal.value.FriendshipLevel <= -3;
};

const suitabilityIconSrc = key => {
  return key ? palStore.backendAssetUrl(`/image/suitabilities/${key.split("::").pop()}`) : '';
};

const currentPaldeck = () => pal.value.Paldeck;

const skinOptions = () => [
  {
    value: '',
    label: palStore.getTranslatedText('Editor_Skin_Default'),
    icon: palStore.backendAssetUrl(`/image/pals/${pal.value.IconKey || 'unknown'}`),
  },
  ...availableSkins().map(skin => ({
    value: skin.SkinName,
    label: skin.SkinName,
    icon: palStore.backendAssetUrl(skin.Invalid
      ? '/image/pals/unknown'
      : `/image/pals/skin-${skin.SkinName}`),
  })),
]

const passiveSkillCategoryKey = group => ({
  pal: 'Editor_Passive_Category_Pal',
  passive: 'Editor_Passive_Category_Regular',
  partner: 'Editor_Passive_Category_Partner',
}[group] || 'Editor_Passive_Skills')

const passiveSkillOptions = () => palStore.PASSIVE_SKILLS_LIST
  .filter(skill => !palStore.HIDE_INVALID_OPTIONS || !skill.Invalid)
  .map(skill => ({
  value: skill.InternalName,
  label: skill.I18n[0],
  description: skill.I18n[1],
  meta: palStore.HIDE_INVALID_OPTIONS ? '' : skill.InternalName,
  tone: palStore.passiveTier(skill.Rating),
  group: palStore.getTranslatedText(passiveSkillCategoryKey(skill.Group)),
  }))

function activeSkillMetadata(skill = {}) {
  const badges = palStore.skillBadges(skill, pal.value.IsHuman)
  const metadata = [
    ...badges
      .filter(badge => badge !== 'exclusive')
      .map(badge => palStore.getTranslatedText(palStore.skillBadgeTranslationKey(badge))),
    `${palStore.getTranslatedText('Editor_Skill_ATK')}${skill.Power}`,
    `${palStore.getTranslatedText('Editor_Skill_CD')}${skill.CT}`,
  ]

  if (badges.includes('exclusive')) {
    metadata.push(palStore.getTranslatedText(palStore.skillBadgeTranslationKey('exclusive')))
    if (skill.LearnerNames?.length) metadata.push(skill.LearnerNames.join(' / '))
  }

  return metadata.join(' · ')
}

const activeSkillSelectOptions = () => activeSkillOptions().map(skill => {
  const element = palStore.elementIconKey(skill.Element)
  return {
    value: skill.InternalName,
    label: skill.I18n[0],
    description: activeSkillMetadata(skill),
    tooltip: skill.I18n[1],
    meta: palStore.HIDE_INVALID_OPTIONS ? '' : skill.InternalName,
    searchMeta: skill.Element,
    disabled: !canSelectActiveSkill(skill),
    icon: element ? palStore.backendAssetUrl(`/image/elements/Element_${element}`) : '',
  }
})

const specialTypeLabel = key => palStore.getTranslatedText(`Editor_Variant_${key}`);

const portraitBorder = pal => pal.IsAwakening
  ? 'var(--editor-color-awakened)'
  : pal.IsBOSS
  ? 'var(--editor-color-danger)'
  : pal.IsRarePal ? 'var(--editor-color-lucky)' : 'var(--editor-color-border)'

</script>

<template>
  <div class="pal-editor">
    <section data-testid="pal-basic-info" class="pal-basic-info editor-surface">
      <header class="editor-summary">
        <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${pal.IconAccessKey}`)"
          :alt="palStore.PAL_STATIC_DATA[pal.DataAccessKey]?.I18n || pal.DataAccessKey"
          size="5.5rem" :border-color="portraitBorder(pal)"
          :glow-color="pal.IsAwakening ? 'var(--editor-color-awakened)' : ''">
          <template #top-left>
            <img v-if="pal.IsBOSS" :src="palStore.backendAssetUrl('/image/ui/boss')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-else-if="pal.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #top-right>
            <img v-if="pal.FavoriteIndex > 0" class="game-priority-icon"
              :src="palStore.backendAssetUrl(`/image/ui/priority-${pal.FavoriteIndex}`)" alt=""
              @error="$event.currentTarget.hidden = true">
            <img v-else-if="pal.IsBOSS && pal.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #bottom-left>
            <img v-if="pal.FavoriteIndex > 0 && pal.IsBOSS && pal.IsRarePal" class="game-lucky-icon"
              :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-if="pal.IsImportedCharacter" class="game-dna-icon"
              :src="palStore.backendAssetUrl('/image/ui/dna')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
        </PalPortrait>
        <div class="editor-summary__identity">
          <span class="editor-summary__eyebrow">
            {{ currentPaldeck() ? `PAL ${currentPaldeck()}` : palStore.getTranslatedText("Editor_Basic_Info") }}
          </span>
          <h2 class="editor-summary__title" :title="pal.InternalName">
            {{ palStore.PAL_STATIC_DATA[pal.DataAccessKey]?.I18n ||
              pal.DataAccessKey }}
          </h2>
          <code class="editor-summary__meta">{{ pal.InternalName }}</code>
          <div class="pal-basic-tags">
            <span class="editor-tag" v-if="palStore.palElementKeys(pal.DataAccessKey).length">
              <img v-for="element in palStore.palElementKeys(pal.DataAccessKey)"
                :key="element" class="element-icon" :src="palStore.backendAssetUrl(`/image/elements/Element_${element}`)" :alt="element">
            </span>
            <span class="editor-tag" v-if="pal.Level">Lv. {{ pal.Level }}</span>
            <span class="editor-tag"
              v-if="!pal.IsHuman && palStore.specialTypeKeys(pal).length">
              {{ palStore.specialTypeKeys(pal).map(specialTypeLabel).join(' · ') }}
            </span>
          </div>
        </div>
        <div class="editor-summary__actions">
          <button id="maximize_pal_btn" class="editor-button editor-button--primary" @click="palStore.maximizePal" :aria-label="palStore.getTranslatedText('Editor_Btn_Maximize_Pal')">
            <UiIcon name="maximum" /> <span class="editor-button__label">{{ palStore.getTranslatedText("Editor_Btn_Maximize_Pal") }}</span>
          </button>
          <button id="dupe_btn" class="editor-button editor-button--secondary" @click="palStore.dupePal"
            :aria-label="palStore.getTranslatedText('Editor_Btn_Dupe_Pal')">
            <UiIcon name="copy" /> <span class="editor-button__label">{{ palStore.getTranslatedText("Editor_Btn_Dupe_Pal") }}</span>
          </button>
          <button id="move_btn" class="editor-button editor-button--secondary" @click="showMoveDialog = true"
            :disabled="moveBlocked" :aria-label="palStore.getTranslatedText('Editor_Move_Pal')">
            <UiIcon name="forward" /> <span class="editor-button__label">{{ palStore.getTranslatedText("Editor_Move_Pal") }}</span>
          </button>
          <button id="dump_btn" class="editor-button editor-button--secondary" @click="palStore.dumpPalData" :aria-label="palStore.getTranslatedText('Editor_Btn_Export_Data')">
            <UiIcon name="export" /> <span class="editor-button__label">{{ palStore.getTranslatedText("Editor_Btn_Export_Data") }}</span>
          </button>
          <button id="del_btn" class="editor-button editor-button--danger" @click="palStore.delPal" :aria-label="palStore.getTranslatedText('Editor_Btn_Delete_Pal')">
            <UiIcon name="delete" /> <span class="editor-button__label">{{ palStore.getTranslatedText("Editor_Btn_Delete_Pal") }}</span>
          </button>
        </div>
      </header>

      <section class="editor-section">
        <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Basic_Info") }}</h3>
        <div class="editor-field">
          <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Species") }}</span>
          <div class="editor-field__control">
            <PalSpeciesSelector
              v-model="speciesSelection"
              :rows="palStore.PAL_STATIC_DATA_LIST"
              :hide-invalid="palStore.HIDE_INVALID_OPTIONS"
              :locale="palStore.I18n"
              @apply="palStore.changeSpecies"
            />
          </div>
        </div>
      </section>

      <div class="pal-basic-grid">
        <section class="editor-section">
          <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Identity_Appearance") }}</h3>
          <div class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Nickname") }}</span>
            <input class="editor-control" type="text" name="NickName" v-model="pal.NickName"
              :placeholder="pal.I18nName">
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon" @click="palStore.updatePal"
                name="NickName" :value="pal.NickName"
                :aria-label="palStore.getTranslatedText('Editor_Nickname')"><UiIcon name="check" /></button>
            </div>
          </div>
          <div v-if="pal.storageKind !== 'global_palbox'" class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_ImportedCharacter") }}</span>
            <span class="editor-tag">
              <img v-if="pal.IsImportedCharacter" class="game-icon" :src="palStore.backendAssetUrl('/image/ui/dna')" alt="">
              <template v-else>-</template>
            </span>
            <div class="editor-field__actions">
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': pal.IsImportedCharacter }]"
                name="IsImportedCharacter"
                :aria-label="palStore.getTranslatedText('Editor_ImportedCharacter')"
                :aria-pressed="pal.IsImportedCharacter"
                @click="updateRange('IsImportedCharacter', !pal.IsImportedCharacter)">
                <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/dna')" alt="">
              </button>
            </div>
          </div>
          <div class="editor-field" v-if="availableSkins().length || pal.SkinName">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Skin") }}</span>
            <SearchSelect ref="skinSelect" v-model="pal.SkinName"
              :options="skinOptions()" :placeholder="palStore.getTranslatedText('Editor_Skin_Default')"
              :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
              :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
              :aria-label="palStore.getTranslatedText('Editor_Skin')"
              :close-on-select="false">
              <template #actions>
                <button class="editor-button editor-button--icon editor-button--primary"
                  @click="applySkin" name="SkinName"
                  :aria-label="palStore.getTranslatedText('Editor_Skin')"><UiIcon name="plus" /></button>
              </template>
            </SearchSelect>
          </div>
          <div class="editor-field" v-if="pal.Gender || !palStore.HIDE_INVALID_OPTIONS">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Gender") }}</span>
            <span class="editor-tag" v-if="palStore.genderKey(pal.Gender)">
              <img class="game-icon" :src="palStore.backendAssetUrl(`/image/ui/gender-${palStore.genderKey(pal.Gender)}`)" alt="">
            </span>
            <div class="editor-field__actions">
              <button class="editor-button editor-button--primary editor-button--icon"
                @click="palStore.swapGender" name="Gender"
                :aria-label="palStore.getTranslatedText('Editor_Gender')"><UiIcon name="refresh" /></button>
            </div>
          </div>
          <div class="editor-field">
            <span class="editor-field__label">{{ palStore.getTranslatedText("PalList_Sort_Priority") }}</span>
            <div class="pal-priority-control" role="group" :aria-label="palStore.getTranslatedText('PalList_Sort_Priority')">
              <button v-for="priority in [0, 1, 2, 3]" :key="priority" type="button"
                :class="['editor-button', pal.FavoriteIndex === priority ? 'editor-button--primary' : 'editor-button--secondary']"
                :aria-label="`${palStore.getTranslatedText('PalList_Sort_Priority')}: ${['—', 'I', 'II', 'III'][priority]}`"
                :aria-pressed="pal.FavoriteIndex === priority"
                @click="updateRange('FavoriteIndex', priority)">
                <span v-if="priority === 0">—</span>
                <img v-else class="game-priority-icon"
                  :src="palStore.backendAssetUrl(`/image/ui/priority-${priority}`)"
                  :alt="['—', 'I', 'II', 'III'][priority]">
              </button>
            </div>
          </div>
        </section>

        <section class="editor-section">
          <h3 class="editor-section__heading">{{ palStore.getTranslatedText("Editor_Growth") }}</h3>
          <div class="editor-stepper">
            <div>
              <span class="editor-field__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/friendship')" alt=""> {{ palStore.getTranslatedText("Editor_Friendship_Level") }}</span>
              <strong class="editor-stepper__value">{{ pal.FriendshipLevel }}</strong>
            </div>
            <div class="editor-stepper__actions">
              <button class="editor-button editor-button--icon" @click="palStore.friendshipDown"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Decrease')"
                :disabled="isMinFriendshipLv()"><UiIcon name="minus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.friendshipUp"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Increase')"
                :disabled="isMaxFriendshipLv()"><UiIcon name="plus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.maxFriendship"
                name="FriendshipLevel" :aria-label="palStore.getTranslatedText('Editor_Btn_Friendship_Max')"
                :disabled="isMaxFriendshipLv()"><UiIcon name="maximum" /></button>
            </div>
          </div>
          <div class="editor-stepper" v-if="pal.Level">
            <div>
              <span class="editor-field__label">Lv.</span>
              <strong class="editor-stepper__value">{{ pal.Level }}</strong>
            </div>
            <div class="editor-stepper__actions">
              <button class="editor-button editor-button--icon" @click="palStore.palLevelDown"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Decrease')"
                :disabled="isMinLv()"><UiIcon name="minus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.palLevelUp"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Increase')"
                :disabled="isMaxLv()"><UiIcon name="plus" /></button>
              <button class="editor-button editor-button--icon" @click="palStore.palMaxLevel"
                name="Level" :aria-label="palStore.getTranslatedText('Editor_Btn_Level_Max')"
                :disabled="isMaxLv()"><UiIcon name="maximum" /></button>
            </div>
          </div>
          <div class="editor-field editor-field--value" v-if="!pal.IsHuman">
            <span class="editor-field__label">{{ palStore.getTranslatedText("Editor_Variant") }}</span>
            <span class="editor-tag">
              {{ palStore.specialTypeKeys(pal).map(specialTypeLabel).join(' · ') || '-' }}
            </span>
            <div class="editor-field__actions">
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': pal.IsBOSS }]"
                @click="palStore.swapBoss" name="IsBOSS"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Boss')"
                :aria-pressed="pal.IsBOSS"
                v-if="canToggleBossVariant(pal)"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/boss')" alt=""></button>
              <button :class="['editor-button editor-button--secondary editor-button--icon editor-button--variant', { 'is-active': pal.IsRarePal }]"
                @click="palStore.swapRare" name="IsRarePal"
                :aria-label="palStore.getTranslatedText('Editor_Btn_Toggle_Rare')"
                :aria-pressed="pal.IsRarePal"
                v-if="canToggleBossVariant(pal)"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/rare')" alt=""></button>
            </div>
          </div>
        </section>
      </div>
      <div class="editor-stat-grid">
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-health')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_HP") }}</span><strong class="editor-stat__value">{{ pal.ComputedMaxHP / 1000 }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_ATK") }}</span><strong class="editor-stat__value">{{ pal.ComputedAttack }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_DEF") }}</span><strong class="editor-stat__value">{{ pal.ComputedDefense }}</strong></div>
        <div class="editor-stat"><span class="editor-stat__label"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-work-speed')" alt=""> {{ palStore.getTranslatedText("Editor_Estimated_WorkSpeed") }}</span><strong class="editor-stat__value">{{ pal.ComputedCraftSpeed }}</strong></div>
      </div>

      <details class="editor-disclosure"
        :open="palStore.PAL_SAVE_DETAILS_OPEN"
        @toggle="palStore.PAL_SAVE_DETAILS_OPEN = $event.currentTarget.open">
        <summary>{{ palStore.getTranslatedText("Editor_Save_Details") }}</summary>
        <div class="pal-technical-grid">
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_CharacterID") }}</span><code>{{ pal.CharacterID }}</code></div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_ID") }}</span><code>{{ pal.InstanceId }}</code></div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Guild_ID") }}</span><code>{{ guildLabel }}</code></div>
          <div class="pal-technical-slot">
            <span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Slot") }}</span>
            <div class="pal-technical-location__value">
              <code>{{ technicalContainer }} @ {{ technicalSlot }}</code>
            </div>
            <small v-if="pal.IsExpeditionPal">
              {{ palStore.getTranslatedText('Editor_Move_Blocked_Expedition') }}
            </small>
            <small v-else-if="!pal.storageKey">
              {{ palStore.getTranslatedText('Editor_Move_Blocked_Anomaly') }}
            </small>
          </div>
          <div><span class="editor-disclosure__label">{{ palStore.getTranslatedText("Editor_Pal_Owner") }}</span><span>{{ ownerLabel }}</span></div>
        </div>
      </details>

      <PalContainerMoveDialog v-if="showMoveDialog" @close="showMoveDialog = false" />

      <div class="pal-health-actions" v-if="pal.HasWorkerSick || pal.IsFaintedPal">
        <button class="editor-button editor-button--primary" v-if="pal.HasWorkerSick"
          @click="palStore.updatePal" name="HasWorkerSick">
          <img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/heal')" alt=""> {{ palStore.getTranslatedText("Editor_Btn_Heal_Pal") }}
        </button>
        <button class="editor-button editor-button--primary" v-if="pal.IsFaintedPal"
          @click="palStore.updatePal" name="IsFaintedPal">
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
            <strong>{{ pal.Talent_HP }}</strong>
            <SegmentedRange name="Talent_HP" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255" v-model="pal.Talent_HP"
              @change="updateRange('Talent_HP', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_IV_DEF") }}</span>
            <strong>{{ pal.Talent_Defense }}</strong>
            <SegmentedRange name="Talent_Defense" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255" v-model="pal.Talent_Defense"
              @change="updateRange('Talent_Defense', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_IV_ATK") }}</span>
            <strong>{{ pal.Talent_Shot }}</strong>
            <SegmentedRange name="Talent_Shot" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255" v-model="pal.Talent_Shot"
              @change="updateRange('Talent_Shot', $event)" />
          </label>
          <label class="range-control" v-if="!palStore.HIDE_INVALID_OPTIONS">
            <span>{{ palStore.getTranslatedText("Editor_IV_MELEE") }}</span>
            <strong>{{ pal.Talent_Melee }}</strong>
            <SegmentedRange name="Talent_Melee" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? 100 : 255" v-model="pal.Talent_Melee"
              @change="updateRange('Talent_Melee', $event)" />
          </label>
        </div>
        <div class="pal-inline-action" v-if="!pal.IsHuman">
          <span>{{ palStore.getTranslatedText("Editor_Awakening") }}</span>
          <strong>{{ pal.IsAwakening ? palStore.getTranslatedText("Editor_Awakened") : "-" }}</strong>
          <button class="editor-button editor-button--icon" @click="palStore.toggleAwakening"
            name="IsAwakening" :aria-label="palStore.getTranslatedText('Editor_Awakening')"><UiIcon name="refresh" /></button>
        </div>
      </section>

      <section class="pal-panel editor-surface">
        <h2 class="pal-panel__heading"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/soul')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_Upgrade") }}</h2>
        <div class="range-grid">
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-health')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_HP") }}</span>
            <strong>{{ pal.Rank_HP }}</strong>
            <SegmentedRange name="Rank_HP" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" v-model="pal.Rank_HP"
              @change="updateRange('Rank_HP', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-attack')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_ATK") }}</span>
            <strong>{{ pal.Rank_Attack }}</strong>
            <SegmentedRange name="Rank_Attack" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" v-model="pal.Rank_Attack"
              @change="updateRange('Rank_Attack', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-defense')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_DEF") }}</span>
            <strong>{{ pal.Rank_Defence }}</strong>
            <SegmentedRange name="Rank_Defence" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" v-model="pal.Rank_Defence"
              @change="updateRange('Rank_Defence', $event)" />
          </label>
          <label class="range-control">
            <span><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/stat-work-speed')" alt=""> {{ palStore.getTranslatedText("Editor_Souls_CraftSpeed") }}</span>
            <strong>{{ pal.Rank_CraftSpeed }}</strong>
            <SegmentedRange name="Rank_CraftSpeed" :min="0" :max="palStore.HIDE_INVALID_OPTIONS ? palStore.MAX_SOULS_LEVEL : 255" v-model="pal.Rank_CraftSpeed"
              @change="updateRange('Rank_CraftSpeed', $event)" />
          </label>
        </div>
        <h3 class="pal-panel__subheading"><img class="game-icon" :src="palStore.backendAssetUrl('/image/ui/condense')" alt=""> {{ palStore.getTranslatedText("Editor_Condenser") }}</h3>
        <label class="range-control range-control--wide">
          <span>{{ palStore.getTranslatedText("Editor_Condenser_Rank") }}</span>
          <strong>{{ pal.Rank - 1 }}</strong>
          <SegmentedRange name="Rank" :min="1" :max="palStore.HIDE_INVALID_OPTIONS ? 5 : 255" v-model="pal.Rank"
            @change="updateRange('Rank', $event)" />
        </label>
      </section>
    </div>

    <section class="pal-panel editor-surface"
      v-if="palStore.PAL_STATIC_DATA[pal.DataAccessKey]?.Suitabilities">
      <div class="pal-panel__header">
        <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Suitabilities") }}</h2>
        <button class="editor-button editor-button--primary" type="button"
          @click="palStore.maxSuitabilities">
          <UiIcon name="maximum" /> {{ palStore.getTranslatedText("Editor_Suitabilities_Max") }}
        </button>
      </div>
      <div class="suitability-grid">
        <div class="suitability-control" v-for="(value, key) in pal.Suitabilities" :key="key"
          v-show="palStore.HIDE_INVALID_OPTIONS || key != 'EPalWorkSuitability::OilExtraction'">
          <img class="suitability-icon" :src="suitabilityIconSrc(key)" :alt="key.split('::').pop()" :title="key.split('::').pop()">
          <strong>{{ value }}</strong>
          <div class="suitability-control__actions">
            <button class="editor-button editor-button--icon" @click="palStore.suitabilityDown" :name="key"
              :aria-label="`${key} -`" :disabled="isMinSuit(key)"><UiIcon name="minus" /></button>
            <button class="editor-button editor-button--icon" @click="palStore.suitabilityUp" :name="key"
              :aria-label="`${key} +`" :disabled="isMaxSuit(key)"><UiIcon name="plus" /></button>
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
          <article class="skill-card" v-for="skill in pal.PassiveSkillList" :key="skill"
            :title="palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill">
            <span :class="['passive-tier', `passive-tier--${palStore.passiveTier(palStore.PASSIVE_SKILLS[skill]?.Rating)}`]" aria-hidden="true"></span>
            <div class="skill-card__identity">
              <div class="skill-card__title">
                <strong>{{ palStore.PASSIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
                <small v-if="!palStore.HIDE_INVALID_OPTIONS" class="skill-card__internal-name">{{ skill }}</small>
              </div>
              <small>{{ palStore.PASSIVE_SKILLS[skill]?.I18n[1] || skill }}</small>
            </div>
            <button type="button" class="skill-card__remove"
              @click="palStore.removePassiveSkill" :name="skill"
              :aria-label="`${palStore.getTranslatedText('Editor_Passive_Skills')} - ${skill}`">×</button>
          </article>
        </div>
        <div class="skill-add" v-if="!palStore.HIDE_INVALID_OPTIONS || pal.PassiveSkillList.length < 4">
          <SearchSelect ref="passiveSkillSelect" v-model="palStore.PAL_PASSIVE_SELECTED_ITEM" placement="top"
            :options="passiveSkillOptions()" :placeholder="palStore.getTranslatedText('Editor_Select_Skill')"
            :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
            :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
            :aria-label="palStore.getTranslatedText('Editor_Passive_Skills')"
            :close-on-select="false">
            <template #actions>
              <button class="editor-button editor-button--icon editor-button--primary"
                @click="addPassiveSkill" name="add_PassiveSkillList"
                :aria-label="palStore.getTranslatedText('Editor_Passive_Skills')"
                :disabled="!palStore.PAL_PASSIVE_SELECTED_ITEM
                  || pal.PassiveSkillList.includes(palStore.PAL_PASSIVE_SELECTED_ITEM)"><UiIcon name="plus" /></button>
            </template>
          </SearchSelect>
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
          <article class="skill-card" v-for="skill in pal.EquipWaza" :key="skill"
            :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">
            <img v-if="palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)" class="element-icon"
              :src="palStore.backendAssetUrl(`/image/elements/Element_${palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)}`)" alt="">
            <div class="skill-card__identity">
              <div class="skill-card__title">
                <strong>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
                <small v-if="!palStore.HIDE_INVALID_OPTIONS" class="skill-card__internal-name">{{ skill }}</small>
              </div>
              <small>{{ activeSkillMetadata(palStore.ACTIVE_SKILLS[skill]) }}</small>
            </div>
            <button type="button" class="skill-card__remove"
              @click="palStore.removeEquipWaza" :name="skill"
              :aria-label="`${palStore.getTranslatedText('Editor_Equipped_Skills')} - ${skill}`">×</button>
          </article>
        </div>
      </div>

      <div class="skill-section">
        <h2 class="pal-panel__heading">{{ palStore.getTranslatedText("Editor_Mastered_Skills") }}</h2>
        <div class="skill-cards">
          <article v-for="skill in pal.MasteredWaza" :key="skill"
            :class="['skill-card', {
              'skill-card--actionable': showEquipMasteredAction(skill),
              'skill-card--equipable': canEquipMasteredSkill(skill),
            }]"
            :title="palStore.ACTIVE_SKILLS[skill]?.I18n[1] || skill">
            <img v-if="palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)" class="element-icon"
              :src="palStore.backendAssetUrl(`/image/elements/Element_${palStore.elementIconKey(palStore.ACTIVE_SKILLS[skill]?.Element)}`)" alt="">
            <div class="skill-card__identity">
              <div class="skill-card__title">
                <strong>{{ palStore.ACTIVE_SKILLS[skill]?.I18n[0] || skill }}</strong>
                <small v-if="!palStore.HIDE_INVALID_OPTIONS" class="skill-card__internal-name">{{ skill }}</small>
              </div>
              <small>{{ activeSkillMetadata(palStore.ACTIVE_SKILLS[skill]) }}</small>
            </div>
            <div v-if="showEquipMasteredAction(skill)" class="skill-card__actions" :title="activeSkillEquipTitle(skill)">
              <button
                type="button" class="editor-button editor-button--icon skill-card__equip"
                @click="palStore.addEquipWaza" :name="skill"
                :aria-label="`${palStore.getTranslatedText('Editor_Equipped_Skills')} + ${skill}`"
                :disabled="!canSelectActiveSkill(palStore.ACTIVE_SKILLS[skill]) || isEquipSkillFull()"><UiIcon name="plus" /></button>
            </div>
            <button type="button" class="skill-card__remove"
              @click="palStore.removeMasteredWaza" :name="skill"
              :aria-label="`${palStore.getTranslatedText('Editor_Mastered_Skills')} - ${skill}`">×</button>
          </article>
        </div>
        <div class="skill-add">
          <SearchSelect ref="activeSkillSelect" v-model="palStore.PAL_ACTIVE_SELECTED_ITEM" placement="top"
            :options="activeSkillSelectOptions()" :placeholder="palStore.getTranslatedText('Editor_Select_Skill')"
            :search-placeholder="palStore.getTranslatedText('Editor_Select_Search')"
            :no-results="palStore.getTranslatedText('Editor_Select_No_Results')"
            :aria-label="palStore.getTranslatedText('Editor_Mastered_Skills')"
            :close-on-select="false">
            <template #actions>
              <button class="editor-button editor-button--icon editor-button--primary"
                @click="addActiveSkill" name="add_MasteredWaza"
                :aria-label="palStore.getTranslatedText('Editor_Mastered_Skills')"
                :disabled="!palStore.PAL_ACTIVE_SELECTED_ITEM
                  || pal.MasteredWaza.includes(palStore.PAL_ACTIVE_SELECTED_ITEM)
                  || !canSelectActiveSkill(palStore.ACTIVE_SKILLS[palStore.PAL_ACTIVE_SELECTED_ITEM])"><UiIcon name="plus" /></button>
            </template>
          </SearchSelect>
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

.pal-basic-info {
  max-width: 100%;
  width: 100%;
  container-name: pal-basic-info;
  container-type: inline-size;
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
  align-items: start;
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
  grid-template-columns: 1fr;
}

.pal-technical-slot > .editor-disclosure__label {
  grid-column: 1 / -1;
}

.pal-technical-location__value { min-width: 0; }

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

  .editor-summary__actions .editor-button__label {
    display: none;
  }

  .editor-summary__actions .editor-button {
    flex: none;
    width: var(--editor-control-height);
    padding: 0;
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

.suitability-control__actions {
  display: flex;
  margin-left: auto;
  gap: var(--editor-space-1);
}

.skill-card__actions {
  position: absolute;
  z-index: 2;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  width: 3rem;
  transform: translateX(100%);
  opacity: 0;
  pointer-events: none;
  transition: transform 170ms ease, opacity 120ms ease;
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
  position: relative;
  padding: var(--editor-space-2);
  padding-right: 2rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-subtle);
}

.skill-card--actionable {
  padding-right: var(--editor-space-2);
  overflow: hidden;
}

.skill-card--equipable {
  border-right-color: color-mix(in srgb, var(--editor-color-focus) 72%, var(--editor-color-border));
  background: color-mix(in srgb, var(--editor-color-focus) 5%, var(--editor-color-surface-subtle));
  box-shadow: inset -2px 0 0 color-mix(in srgb, var(--editor-color-focus) 58%, transparent);
}

.skill-card--equipable:hover {
  border-color: color-mix(in srgb, var(--editor-color-focus) 64%, var(--editor-color-border));
  background: color-mix(in srgb, var(--editor-color-focus) 9%, var(--editor-color-surface-subtle));
}

.skill-card--actionable:is(:hover, :focus-within) .skill-card__actions {
  transform: translateX(0);
  opacity: 1;
  pointer-events: auto;
}

.skill-card--actionable:is(:hover, :focus-within) .skill-card__identity {
  padding-right: 3rem;
}

.skill-card--actionable .skill-card__remove {
  right: calc(3rem + .16rem);
}

.skill-card__remove {
  position: absolute;
  z-index: 1;
  top: .12rem;
  right: .16rem;
  display: grid;
  width: 1rem;
  height: 1rem;
  padding: 0;
  border: 0;
  place-items: center;
  color: rgb(255 255 255 / .8);
  background: transparent;
  font-size: 1rem;
  line-height: 1;
  opacity: 0;
  cursor: pointer;
  text-shadow: 0 1px 4px #000;
}

.skill-card:hover .skill-card__remove,
.skill-card__remove:focus-visible {
  opacity: 1;
}

.skill-card__remove:hover { color: #fca5a5; }
.skill-card__remove:disabled { cursor: not-allowed; opacity: .35; }

.skill-card__equip {
  width: 100%;
  min-height: 100%;
  padding: var(--editor-space-3) var(--editor-space-2) var(--editor-space-2);
  border: 0;
  border-left: 1px solid color-mix(in srgb, var(--editor-color-focus) 34%, transparent);
  border-radius: 0 var(--editor-radius-sm) var(--editor-radius-sm) 0;
  color: var(--editor-color-background);
  background: color-mix(in srgb, var(--editor-color-focus) 72%, var(--editor-color-border));
}

.skill-card__equip:hover,
.skill-card__equip:focus-visible {
  color: var(--editor-color-background);
  background: color-mix(in srgb, var(--editor-color-focus) 86%, var(--editor-color-border));
}

.skill-card__equip:disabled {
  border-color: var(--editor-color-border);
  color: var(--editor-color-muted);
  background: var(--editor-color-disabled);
  cursor: not-allowed;
}

.skill-card__identity {
  display: grid;
  gap: 0;
  overflow: hidden;
  transition: padding-right 170ms ease;
}

.skill-card__title {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--editor-space-1);
}

.skill-card__identity strong,
.skill-card__identity small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-card__identity small {
  color: var(--editor-color-muted);
  font-size: .75rem;
  line-height: 1.05;
}

.skill-card__identity .skill-card__internal-name {
  min-width: 0;
  flex: 1;
  color: var(--editor-color-muted);
  font-size: .62rem;
  line-height: 1.25;
  opacity: .55;
}

.skill-add > :first-child {
  min-width: 0;
  flex: 1;
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

@media (hover: none) {
  .skill-card--actionable .skill-card__actions {
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
  }

  .skill-card--actionable .skill-card__identity {
    padding-right: 3rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skill-card__actions,
  .skill-card__identity {
    transition: none;
  }
}
</style>
