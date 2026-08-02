<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import AddPalDialog from '@/components/AddPalDialog.vue'
import PalPortrait from '@/components/modules/PalPortrait.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { filterPalPriority, isCreatedPal, sortPalList } from '@/components/modules/pal-list-order'
import { paldeckForRow } from '@/components/modules/pal-species-selector'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const props = defineProps({ preview: Boolean })
const emit = defineEmits(['toggle'])
const toggleLabel = () => palStore.getTranslatedText(props.preview ? 'PalList_Restore' : 'PalList_Collapse')
const palListContainer = ref(null)
const showAddPalDialog = ref(false)

watch(async () => palStore.SELECTED_PLAYER_ID, async () => {
  await nextTick()
  if (palStore.SHOW_PLAYER_EDIT_FLAG && !palStore.BASE_PAL_BTN_CLK_FLAG) return
  try {
    if (palStore.BASE_PAL_BTN_CLK_FLAG == false) return
    palListContainer.value.querySelector('button:not(:disabled)')?.click()
  } catch (error) {
    return
  }
})

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
      if (palStore.SELECTED_PAL_ID != palStore.SELECTED_PAL_DATA?.InstanceId) {
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
    .filter(pal => filterPalPriority(pal, palStore.PAL_LIST_PRIORITY_FILTER))
    .filter(pal => !palStore.PAL_LIST_CREATED_ONLY || isCreatedPal(pal, palStore.CREATED_PAL_IDS)),
  palStore.PAL_LIST_SORT,
  pal => paldeckForRow(palStore.PAL_STATIC_DATA[pal.DataAccessKeyOG]),
))

watch(
  [
    () => palStore.PAL_LIST_SORT,
    () => palStore.PAL_LIST_PRIORITY_FILTER,
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
</script>

<template>
  <nav class="pal-roster" :aria-label="palStore.getTranslatedText('PalList_Text')">
    <header class="roster-header">
      <button class="roster-title-button" :title="toggleLabel()"
        :aria-label="toggleLabel()" @click="emit('toggle')">
        {{ palStore.getTranslatedText("PalList_Text") }}
      </button>
      <div class="roster-actions">
        <details v-if="!props.preview" class="pal-list-menu">
          <summary class="roster-icon-button"
            :title="palStore.getTranslatedText('PalList_SortFilter')"
            :aria-label="palStore.getTranslatedText('PalList_SortFilter')">
            <UiIcon name="filter" />
          </summary>
          <div class="pal-list-menu__popover">
            <label>
              <span>{{ palStore.getTranslatedText('PalList_Sort') }}</span>
              <select v-model="palStore.PAL_LIST_SORT">
                <option value="paldeck">{{ palStore.getTranslatedText('PalList_Sort_Paldeck') }}</option>
                <option value="location">{{ palStore.getTranslatedText('PalList_Sort_Location') }}</option>
                <option value="priority">{{ palStore.getTranslatedText('PalList_Sort_Priority') }}</option>
              </select>
            </label>
            <label>
              <span>{{ palStore.getTranslatedText('PalList_Filter_Priority') }}</span>
              <select v-model="palStore.PAL_LIST_PRIORITY_FILTER">
                <option value="all">{{ palStore.getTranslatedText('PalList_Filter_All') }}</option>
                <option value="3">III</option>
                <option value="2">II</option>
                <option value="1">I</option>
                <option value="0">{{ palStore.getTranslatedText('PalList_Filter_Unprioritized') }}</option>
              </select>
            </label>
            <label class="pal-list-menu__checkbox">
              <input v-model="palStore.PAL_LIST_CREATED_ONLY" type="checkbox">
              <span>{{ palStore.getTranslatedText('PalList_Filter_Created') }}</span>
            </label>
          </div>
        </details>
        <button class="roster-icon-button" v-if="!palStore.BASE_PAL_BTN_CLK_FLAG"
          :title="palStore.getTranslatedText('PalList_Add')" :aria-label="palStore.getTranslatedText('PalList_Add')"
          :disabled="palStore.LOADING_FLAG" @click="showAddPalDialog = true" name="add_pal">
          <UiIcon name="plus" />
        </button>
      </div>
      <label class="pal-search">
        <UiIcon name="search" />
        <input type="search" v-model="palStore.PAL_LIST_SEARCH_KEYWORD"
          :placeholder="palStore.getTranslatedText('PalList_Search')" :disabled="palStore.LOADING_FLAG">
      </label>
    </header>

    <div class="roster-list" ref="palListContainer">
      <button v-for="pal in visiblePals" :key="pal.InstanceId"
        :class="['pal-row', { male: palStore.genderKey(pal.Gender) === 'male', female: palStore.genderKey(pal.Gender) === 'female', unref: pal.Is_Unref_Pal, 'out-of-container': !pal.in_owner_palbox }]"
        :value="pal.InstanceId" @click="palStore.selectPal(pal.InstanceId)"
        :aria-current="palStore.SELECTED_PAL_ID == pal.InstanceId ? 'true' : undefined"
        :disabled="palStore.SELECTED_PAL_ID == pal.InstanceId || palStore.LOADING_FLAG">
        <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${pal.IconAccessKey}`)" alt="" size="2.5rem"
          :border-color="portraitBorder(pal)"
          :glow-color="pal.IsAwakening ? 'var(--editor-color-awakened)' : ''">
          <template #top-left>
            <img v-if="pal.IsBOSS" :src="palStore.backendAssetUrl('/image/ui/boss')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-else-if="pal.IsRarePal" :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #top-right>
            <img v-if="pal.IsBOSS && pal.IsRarePal" :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #bottom-right>
            <span v-if="pal.IsNewPal" class="new-pal-marker"><UiIcon name="plus" /></span>
          </template>
        </PalPortrait>
        <span class="pal-copy">
          <strong class="pal-name">
            <span>{{ pal.DisplayName }}</span>
          </strong>
          <small>{{ palMetadata(pal) }}</small>
          <span class="sr-only">{{ palStatus(pal) }}</span>
          <span v-if="pal.IsNewPal" class="sr-only">{{ palStore.getTranslatedText('PalList_Status_Unsaved') }}</span>
        </span>
      </button>
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
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-2);
  padding: var(--editor-space-3);
  border-bottom: 1px solid var(--editor-color-border);
}

.roster-title-button {
  margin: 0;
  padding: 0;
  border: 0;
  color: var(--editor-color-muted);
  background: transparent;
  font-size: .8rem;
  letter-spacing: .04em;
  text-transform: uppercase;
  cursor: pointer;
}

.roster-actions {
  display: flex;
  gap: var(--editor-space-1);
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
  right: 0;
  display: grid;
  width: min(15rem, calc(100vw - 2rem));
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-surface-raised);
  box-shadow: var(--editor-shadow-compact);
}

.pal-list-menu__popover label {
  display: grid;
  gap: var(--editor-space-1);
  color: var(--editor-color-muted);
  font-size: .75rem;
}

.pal-list-menu__popover .pal-list-menu__checkbox {
  display: flex;
  align-items: center;
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

.pal-row {
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
  border-color: var(--editor-color-focus);
  color: var(--editor-color-text);
  background: var(--editor-color-surface-raised);
  box-shadow: inset .2rem 0 var(--editor-color-focus), 0 0 .7rem color-mix(in srgb, var(--editor-color-focus) 25%, transparent);
}

.pal-row:disabled {
  cursor: default;
}

.pal-row.male { border-left-color: var(--editor-color-male); }
.pal-row.female { border-left-color: var(--editor-color-female); }
.pal-row.unref { filter: grayscale(1); }
.pal-row.out-of-container small { color: var(--editor-color-success); }
.pal-row[aria-current="true"] small { color: var(--editor-color-muted); }

.new-pal-marker {
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
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
  cursor: pointer;
}

.roster-icon-button:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
  cursor: not-allowed;
}

.pal-search:focus-within,
.pal-row:focus-visible,
.roster-title-button:focus-visible,
.roster-icon-button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@media (max-width: 760px) {
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
