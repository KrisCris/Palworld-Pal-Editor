<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AddPalDialog from '@/components/AddPalDialog.vue'
import PalPortrait from '@/components/modules/PalPortrait.vue'
import { formatContainerLabel } from '@/components/modules/pal-container-label'
import UiIcon from '@/components/modules/UiIcon.vue'
import {
  groupPalList,
  isCreatedPal,
  isEditedPal,
  matchesPalAttributeFilters,
  matchesPalSessionFilter,
  sortPalList,
} from '@/components/modules/pal-list-order'
import { paldeckForRow } from '@/components/modules/pal-species-selector'
import { closeDisclosureOnOutsidePointer } from '@/components/modules/search-select'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const props = defineProps({ preview: Boolean })
const emit = defineEmits(['toggle'])
const toggleLabel = () => palStore.getTranslatedText(props.preview ? 'PalList_Restore' : 'PalList_Collapse')
const palListContainer = ref(null)
const sortMenu = ref(null)
const showAddPalDialog = ref(false)
const attemptedAutoSelectRoster = ref(null)
const activeSpecialRoster = computed(() => palStore.BASE_PAL_BTN_CLK_FLAG
  ? palStore.PAL_BASE_WORKER_BTN
  : palStore.SELECTED_PLAYER_ID === palStore.PAL_GLOBAL_STORAGE_BTN
  ? palStore.PAL_GLOBAL_STORAGE_BTN
  : null)
const activePalFilterCount = computed(() => palStore.PAL_LIST_ATTRIBUTE_FILTERS.length
  + Number(palStore.PAL_LIST_EDITED_ONLY)
  + Number(palStore.PAL_LIST_CREATED_ONLY))
const attributeFilters = Object.freeze([
  { key: 'priority-1', icon: 'priority-1', label: 'I' },
  { key: 'priority-2', icon: 'priority-2', label: 'II' },
  { key: 'priority-3', icon: 'priority-3', label: 'III' },
  { key: 'alpha', icon: 'boss', translation: 'PalList_Filter_Alpha' },
  { key: 'lucky', icon: 'rare', translation: 'PalList_Filter_Lucky' },
  { key: 'dna', icon: 'dna', translation: 'PalList_Filter_DNA' },
  { key: 'human', uiIcon: 'users', translation: 'PalList_Filter_Human' },
])

const toggleAttributeFilter = key => {
  const filters = palStore.PAL_LIST_ATTRIBUTE_FILTERS
  palStore.PAL_LIST_ATTRIBUTE_FILTERS = filters.includes(key)
    ? filters.filter(filter => filter !== key)
    : [...filters, key]
}

const closeSortMenuOnOutsidePointer = event => closeDisclosureOnOutsidePointer(sortMenu.value, event.target)
onMounted(() => window.addEventListener('pointerdown', closeSortMenuOnOutsidePointer))
onBeforeUnmount(() => window.removeEventListener('pointerdown', closeSortMenuOnOutsidePointer))

watch([
  activeSpecialRoster,
  () => palStore.LOADING_FLAG,
], async ([roster, loading], previous = []) => {
  if (roster !== previous[0]) attemptedAutoSelectRoster.value = null
  if (!roster || loading || palStore.SELECTED_PAL_ID || attemptedAutoSelectRoster.value === roster) return
  await nextTick()
  if (palStore.LOADING_FLAG || palStore.SELECTED_PAL_ID || activeSpecialRoster.value !== roster) return
  try {
    const button = palListContainer.value?.querySelector('button:not(:disabled)')
    if (!button) return
    attemptedAutoSelectRoster.value = roster
    button.click()
  } catch (error) {
    return
  }
}, { immediate: true, flush: 'post' })

watch(async () => palStore.UPDATE_PAL_RESELECT_CTR, async () => {
  await nextTick()
  try {
    const button = palListContainer.value.querySelector(`button[value="${palStore.SELECTED_PAL_ID}"]`)
    button?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  } catch (error) {
    return
  }
})

watch(async () => palStore.SELECTED_PAL_ID, async () => {
  await nextTick()
  if (palStore.SHOW_PLAYER_EDIT_FLAG && !palStore.BASE_PAL_BTN_CLK_FLAG) return
  try {
    const button = palListContainer.value.querySelector(`button[value="${palStore.SELECTED_PAL_ID}"]`)
    if (button) {
      if (palStore.SELECTED_PAL_ID != palStore.SELECTED_PAL_DATA?.RecordKey) {
        palStore.selectPal(palStore.SELECTED_PAL_ID, true)
      }
      button.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  } catch (error) {
    return
  }
})

const visiblePals = computed(() => sortPalList(
  Array.from(palStore.PAL_MAP.values())
    .filter(pal => !palStore.isFilteredPal(pal))
    .filter(pal => matchesPalAttributeFilters(pal, palStore.PAL_LIST_ATTRIBUTE_FILTERS))
    .filter(pal => matchesPalSessionFilter(
      pal,
      palStore.PAL_LIST_EDITED_ONLY,
      palStore.PAL_LIST_CREATED_ONLY,
      palStore.EDITED_PAL_IDS,
      palStore.CREATED_PAL_IDS,
    )),
  palStore.PAL_LIST_SORT,
  pal => paldeckForRow(palStore.PAL_STATIC_DATA[pal.DataAccessKeyOG]),
))

const visiblePalGroups = computed(() => groupPalList(
  visiblePals.value,
  palStore.PAL_LIST_SORT,
).map(group => ({
  ...group,
  container: palStore.PAL_CONTAINERS.find(container => container.StorageKey === group.key),
})))
const containerLabel = group => formatContainerLabel(
  group.container || {
    ContainerKind: group.key === 'anomaly' ? 'anomaly' : 'other',
    ContainerLabel: group.label,
  },
  palStore.getTranslatedText,
)

watch(
  [
    () => palStore.PAL_LIST_SORT,
    () => palStore.PAL_LIST_ATTRIBUTE_FILTERS,
    () => palStore.PAL_LIST_EDITED_ONLY,
    () => palStore.PAL_LIST_CREATED_ONLY,
  ],
  async () => {
    await nextTick()
    palListContainer.value
      ?.querySelector(`button[value="${palStore.SELECTED_PAL_ID}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  },
)

function palMetadata(pal) {
  const row = palStore.PAL_STATIC_DATA[pal.DataAccessKeyOG]
  const paldeck = paldeckForRow(row)
  const id = pal.CharacterID || pal.DataAccessKeyOG
  return paldeck ? `PAL ${paldeck} · ${id}` : id
}

const portraitBorder = pal => pal.IsAwakening
  ? 'var(--editor-color-awakened)'
  : pal.IsBOSS
  ? 'var(--editor-color-danger)'
  : pal.IsRarePal ? 'var(--editor-color-lucky)' : 'var(--editor-color-border)'

const palStatus = pal => palStore.getTranslatedText(`PalList_Status_${pal.IsBOSS
  ? pal.IsRarePal ? 'AlphaLucky' : 'Alpha'
  : pal.IsRarePal ? 'Lucky' : 'Ordinary'}`)

const palWasCreated = pal => isCreatedPal(pal, palStore.CREATED_PAL_IDS)
const palWasEdited = pal => isEditedPal(pal, palStore.EDITED_PAL_IDS, palStore.CREATED_PAL_IDS)
const palKey = pal => pal.RecordKey || pal.InstanceId
</script>

<template>
  <nav :class="['pal-roster', { 'pal-roster--preview': preview }]"
    :aria-label="palStore.getTranslatedText('PalList_Text')">
    <header class="roster-header">
      <div class="roster-heading-row">
        <button class="roster-collapse-button" :title="toggleLabel()"
          :aria-label="toggleLabel()" @click="emit('toggle')">
          <UiIcon :name="preview ? 'panel' : 'minus'" />
        </button>
        <h2 class="roster-title">{{ palStore.getTranslatedText("PalList_Text") }}</h2>
        <div class="roster-actions">
          <details ref="sortMenu" class="pal-list-menu">
          <summary class="roster-icon-button" :class="{ 'is-active': activePalFilterCount > 0 }"
            :title="palStore.getTranslatedText('PalList_SortFilter')"
            :aria-label="palStore.getTranslatedText('PalList_SortFilter')">
            <UiIcon name="filter" />
            <span v-if="activePalFilterCount" class="filter-count">{{ activePalFilterCount }}</span>
          </summary>
          <div class="pal-list-menu__popover editor-glass-surface">
            <label>
              <span>{{ palStore.getTranslatedText('PalList_Sort') }}</span>
              <select v-model="palStore.PAL_LIST_SORT">
                <option value="paldeck">{{ palStore.getTranslatedText('PalList_Sort_Paldeck') }}</option>
                <option value="location">{{ palStore.getTranslatedText('PalList_Sort_Location') }}</option>
                <option value="priority">{{ palStore.getTranslatedText('PalList_Sort_Priority') }}</option>
              </select>
            </label>
            <fieldset class="pal-list-menu__attribute-filters">
              <legend>{{ palStore.getTranslatedText('PalList_Filter_Attributes') }}</legend>
              <button v-for="filter in attributeFilters" :key="filter.key" type="button"
                :class="['pal-list-menu__attribute-button', { 'is-active': palStore.PAL_LIST_ATTRIBUTE_FILTERS.includes(filter.key) }]"
                :aria-pressed="palStore.PAL_LIST_ATTRIBUTE_FILTERS.includes(filter.key)"
                :title="filter.translation ? palStore.getTranslatedText(filter.translation) : filter.label"
                :aria-label="filter.translation ? palStore.getTranslatedText(filter.translation) : filter.label"
                @click="toggleAttributeFilter(filter.key)">
                <img v-if="filter.icon" :src="palStore.backendAssetUrl(`/image/ui/${filter.icon}`)" alt=""
                  @error="$event.currentTarget.hidden = true">
                <UiIcon v-else :name="filter.uiIcon" />
                <span>{{ filter.label || palStore.getTranslatedText(filter.translation) }}</span>
              </button>
            </fieldset>
            <div class="pal-list-menu__session-buttons">
              <button class="pal-list-menu__session-button" type="button"
                :aria-pressed="palStore.PAL_LIST_EDITED_ONLY"
                @click="palStore.PAL_LIST_EDITED_ONLY = !palStore.PAL_LIST_EDITED_ONLY">
                <UiIcon name="edit" />
                <span>{{ palStore.getTranslatedText('PalList_Filter_Edited') }}</span>
              </button>
              <button class="pal-list-menu__session-button" type="button"
                :aria-pressed="palStore.PAL_LIST_CREATED_ONLY"
                @click="palStore.PAL_LIST_CREATED_ONLY = !palStore.PAL_LIST_CREATED_ONLY">
                <UiIcon name="plus" />
                <span>{{ palStore.getTranslatedText('PalList_Filter_Created') }}</span>
              </button>
            </div>
          </div>
          </details>
          <button class="roster-icon-button"
            :title="palStore.getTranslatedText('PalList_Add')" :aria-label="palStore.getTranslatedText('PalList_Add')"
            :disabled="palStore.LOADING_FLAG" @click="showAddPalDialog = true" name="add_pal">
            <UiIcon name="plus" />
          </button>
        </div>
      </div>
      <label class="pal-search">
        <UiIcon name="search" />
        <input type="search" v-model="palStore.PAL_LIST_SEARCH_KEYWORD"
          :placeholder="palStore.getTranslatedText('PalList_Search')" :disabled="palStore.LOADING_FLAG">
      </label>
    </header>

    <div class="roster-list" ref="palListContainer">
      <template v-for="group in visiblePalGroups" :key="group.key">
      <h3 v-if="group.label" class="container-heading">
        <span>{{ containerLabel(group) }}</span>
        <small v-if="group.container">{{ group.container.Occupied }} / {{ group.container.Size }}</small>
      </h3>
      <button v-for="pal in group.pals" :key="palKey(pal)"
        :class="['pal-row', { male: palStore.genderKey(pal.Gender) === 'male', female: palStore.genderKey(pal.Gender) === 'female', unref: pal.Is_Unref_Pal, 'out-of-container': !pal.in_owner_palbox }]"
        :value="palKey(pal)" @click="palStore.selectPal(palKey(pal))"
        :aria-current="palStore.SELECTED_PAL_ID == palKey(pal) ? 'true' : undefined"
        :disabled="palStore.SELECTED_PAL_ID == palKey(pal) || palStore.LOADING_FLAG">
        <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${pal.IconAccessKey}`)" alt="" size="2.5rem"
          :border-color="portraitBorder(pal)"
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
          <template #bottom-right>
            <span v-if="palWasCreated(pal)" class="new-pal-marker"><UiIcon name="plus" /></span>
            <span v-else-if="palWasEdited(pal)" class="edited-pal-marker"><UiIcon name="edit" /></span>
          </template>
        </PalPortrait>
        <span class="pal-copy">
          <strong class="pal-name">
            <span>{{ pal.DisplayName }}</span>
            <span v-if="pal.IsExpeditionPal" class="pal-location-badge pal-location-badge--expedition">
              {{ palStore.getTranslatedText('PalList_Expedition') }}
            </span>
            <span v-if="pal.LocationStatus && pal.LocationStatus !== 'ok'"
              class="pal-location-badge pal-location-badge--anomaly" :title="pal.LocationAnomaly">
              {{ palStore.getTranslatedText('PalList_Location_Anomaly') }}
            </span>
          </strong>
          <small>{{ palMetadata(pal) }}</small>
          <span class="sr-only">{{ palStatus(pal) }}</span>
          <span v-if="palWasCreated(pal)" class="sr-only">{{ palStore.getTranslatedText('PalList_Status_Unsaved') }}</span>
          <span v-else-if="palWasEdited(pal)" class="sr-only">{{ palStore.getTranslatedText('PalList_Status_Edited') }}</span>
        </span>
      </button>
      </template>
    </div>
    <AddPalDialog v-if="showAddPalDialog" @close="showAddPalDialog = false" />
  </nav>
</template>

<style scoped>
.pal-roster {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}

.roster-header {
  z-index: 1;
  display: grid;
  gap: var(--editor-space-2);
  padding: var(--editor-space-3);
  border-bottom: 1px solid var(--editor-color-border);
}

.roster-heading-row {
  position: relative;
  display: grid;
  min-height: 2rem;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-2);
}

.roster-title {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: calc(100% - 8rem);
  margin: 0;
  overflow: hidden;
  color: var(--editor-color-muted);
  font-size: .8rem;
  font-weight: 400;
  letter-spacing: .04em;
  text-overflow: ellipsis;
  text-transform: uppercase;
  transform: translate(-50%, -50%);
  white-space: nowrap;
}

.roster-collapse-button {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-muted);
  background: transparent;
  cursor: pointer;
  transition: color .15s ease, background-color .15s ease;
}

.roster-collapse-button:hover {
  color: var(--editor-color-text);
  background: var(--editor-color-control-hover);
}

.roster-actions {
  display: flex;
  gap: var(--editor-space-1);
  grid-column: 3;
}

.pal-list-menu {
  position: relative;
}

.pal-list-menu summary {
  list-style: none;
}

.pal-list-menu summary::-webkit-details-marker {
  display: none;
}

.pal-list-menu__popover {
  position: absolute;
  z-index: 30;
  top: calc(100% + var(--editor-space-2));
  left: 0;
  display: grid;
  width: min(22rem, calc(100vw - 2rem));
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  box-shadow: var(--editor-shadow-compact);
}

.pal-roster--preview .pal-list-menu__popover {
  right: 0;
  left: auto;
  width: min(13rem, calc(100vw - 2rem));
}

.pal-list-menu__popover label {
  display: grid;
  gap: var(--editor-space-1);
  color: var(--editor-color-muted);
  font-size: .75rem;
}

.pal-list-menu__session-buttons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--editor-space-1);
  padding-top: var(--editor-space-2);
  border-top: 1px solid var(--editor-color-border);
}

.pal-list-menu__attribute-filters {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--editor-space-1);
  margin: 0;
  padding: 0;
  border: 0;
}

.pal-list-menu__attribute-filters legend {
  grid-column: 1 / -1;
  margin-bottom: var(--editor-space-1);
  color: var(--editor-color-muted);
  font-size: .75rem;
}

.pal-list-menu__attribute-button {
  display: grid;
  min-width: 0;
  min-height: 3rem;
  place-items: center;
  gap: .15rem;
  padding: .3rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-muted);
  background: var(--editor-color-control);
  font: inherit;
  font-size: .65rem;
  cursor: pointer;
}

.pal-list-menu__attribute-button:hover {
  background: var(--editor-color-control-hover);
}

.pal-list-menu__attribute-button.is-active {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-primary);
  background: color-mix(in srgb, var(--editor-color-primary) 15%, var(--editor-color-control));
}

.pal-list-menu__attribute-button img,
.pal-list-menu__attribute-button .ui-icon {
  width: 1.25rem;
  height: 1.25rem;
  object-fit: contain;
}

.pal-list-menu__session-button {
  display: flex;
  min-width: 0;
  min-height: 2.5rem;
  align-items: center;
  justify-content: center;
  gap: var(--editor-space-1);
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  font: inherit;
  font-size: .72rem;
  cursor: pointer;
}

.pal-list-menu__session-button:hover {
  background: var(--editor-color-control-hover);
}

.pal-list-menu__session-button[aria-pressed="true"] {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.pal-list-menu__session-button .ui-icon {
  flex: 0 0 auto;
}

.pal-list-menu__session-button span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.pal-list-menu__popover select {
  min-width: 0;
  min-height: 2.25rem;
  padding: 0 var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.pal-search {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: var(--editor-space-2);
  min-height: 2.25rem;
  padding: 0 var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-control);
}

.pal-search input {
  min-width: 0;
  border: 0;
  outline: 0;
  color: var(--editor-color-text);
  background: transparent;
}

.roster-list {
  position: relative;
  z-index: 0;
  display: grid;
  min-height: 0;
  align-content: start;
  gap: var(--editor-space-1);
  overflow-y: auto;
  padding: var(--editor-space-2);
}

.container-heading {
  display: flex;
  grid-column: 1 / -1;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-2);
  margin: var(--editor-space-2) var(--editor-space-1) 0;
  color: var(--editor-color-muted);
  font-size: .72rem;
  font-weight: 600;
}

.container-heading span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.container-heading small {
  flex: none;
  font-weight: 400;
}

.pal-row {
  --pal-row-accent: var(--editor-color-focus);
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr);
  align-items: center;
  gap: var(--editor-space-2);
  min-height: 3.25rem;
  padding: var(--editor-space-1) var(--editor-space-2);
  border: 1px solid transparent;
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
  text-align: left;
  cursor: pointer;
}

.pal-row:hover {
  background: var(--editor-color-control-hover);
}

.pal-row[aria-current="true"] {
  border-color: var(--pal-row-accent);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
  box-shadow: inset .2rem 0 var(--pal-row-accent), 0 0 .7rem color-mix(in srgb, var(--pal-row-accent) 25%, transparent);
}

.pal-row:disabled {
  cursor: default;
}

.pal-row.male { --pal-row-accent: var(--editor-color-male); border-left-color: var(--pal-row-accent); }
.pal-row.female { --pal-row-accent: var(--editor-color-female); border-left-color: var(--pal-row-accent); }
.pal-row.unref { filter: grayscale(1); }
.pal-row.out-of-container small { color: var(--editor-color-success); }
.pal-row[aria-current="true"] small { color: var(--editor-color-muted); }

.new-pal-marker,
.edited-pal-marker {
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
  border: 1px solid var(--editor-color-background);
  border-radius: 50%;
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
  font-size: .7rem;
}

.edited-pal-marker {
  background: var(--editor-color-success);
}

.pal-copy {
  display: grid;
  min-width: 0;
}

.pal-name {
  display: flex;
  align-items: center;
  gap: var(--editor-space-1);
}

.pal-name span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.pal-location-badge {
  flex: 0 0 auto;
  padding: .1rem .35rem;
  border-radius: 999px;
  color: var(--editor-color-background);
  background: var(--editor-color-muted);
  font-size: .58rem;
  font-weight: 700;
}

.pal-location-badge--expedition { background: var(--editor-color-primary); }
.pal-location-badge--anomaly { background: var(--editor-color-danger); }

.pal-copy strong,
.pal-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pal-copy small {
  color: var(--editor-color-muted);
  font-size: .7rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.roster-icon-button {
  position: relative;
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-muted);
  background: var(--editor-color-control);
  cursor: pointer;
}

.filter-count {
  position: absolute;
  top: -.3rem;
  right: -.3rem;
  display: grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  padding: 0 .2rem;
  border-radius: 999px;
  color: var(--editor-color-primary);
  background: var(--editor-color-text);
  font-size: .6rem;
  font-weight: 700;
}

.roster-icon-button:hover {
  color: var(--editor-color-text);
  background: var(--editor-color-control-hover);
}

.roster-icon-button.is-active {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.roster-icon-button:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
  cursor: not-allowed;
}

.pal-search:focus-within,
.pal-row:focus-visible,
.roster-collapse-button:focus-visible,
.roster-icon-button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@media (max-width: 760px) {
  .pal-list-menu__popover {
    right: 0;
    left: auto;
  }

  .roster-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 480px) {
  .roster-list {
    grid-template-columns: 1fr;
  }
}
</style>
