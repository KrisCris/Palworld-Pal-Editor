<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'

import PalPortrait from '@/components/modules/PalPortrait.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { paldeckForRow } from '@/components/modules/pal-species-selector'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const emit = defineEmits(['collapse'])
const palListContainer = ref(null)

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
    if (button && !palStore.isElementInViewport(button)) button.scrollIntoView({ behavior: 'smooth' })
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
      if (!palStore.isElementInViewport(button)) button.scrollIntoView({ behavior: 'smooth' })
    }
  } catch (error) {
    return
  }
})

onMounted(async () => {
  await nextTick()
  await nextTick()
  await nextTick()
  if (palStore.SHOW_PLAYER_EDIT_FLAG && !palStore.BASE_PAL_BTN_CLK_FLAG) return
  palListContainer.value.querySelector('button:not(:disabled)')?.click()
})

const filteredPals = () => Array.from(palStore.PAL_MAP.values())
  .filter(pal => !palStore.isFilteredPal(pal))

function palMetadata(pal) {
  const row = palStore.PAL_STATIC_DATA[pal.DataAccessKeyOG]
  const paldeck = paldeckForRow(row)
  const id = pal.CharacterID || pal.DataAccessKeyOG
  return paldeck ? `PAL ${paldeck} · ${id}` : id
}

const portraitBorder = pal => pal.IsBOSS
  ? 'var(--editor-color-danger)'
  : pal.IsRarePal ? 'var(--editor-color-lucky)' : 'var(--editor-color-border)'

const palStatus = pal => palStore.getTranslatedText(`PalList_Status_${pal.IsBOSS
  ? pal.IsRarePal ? 'AlphaLucky' : 'Alpha'
  : pal.IsRarePal ? 'Lucky' : 'Ordinary'}`)
</script>

<template>
  <nav class="pal-roster" :aria-label="palStore.getTranslatedText('PalList_Text')">
    <header class="roster-header">
      <h2>{{ palStore.getTranslatedText("PalList_Text") }}</h2>
      <div class="roster-actions">
        <button class="roster-icon-button" :title="palStore.getTranslatedText('PalList_Collapse')"
          :aria-label="palStore.getTranslatedText('PalList_Collapse')" @click="emit('collapse')">
          <UiIcon name="back" />
        </button>
        <button class="roster-icon-button" v-if="!palStore.BASE_PAL_BTN_CLK_FLAG"
          :title="palStore.getTranslatedText('PalList_Add')" :aria-label="palStore.getTranslatedText('PalList_Add')"
          :disabled="palStore.LOADING_FLAG" @click="palStore.addPal" name="add_pal">
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
      <button v-for="pal in filteredPals()" :key="pal.InstanceId"
        :class="['pal-row', { male: palStore.genderKey(pal.Gender) === 'male', female: palStore.genderKey(pal.Gender) === 'female', unref: pal.Is_Unref_Pal, 'out-of-container': !pal.in_owner_palbox }]"
        :value="pal.InstanceId" @click="palStore.selectPal(pal.InstanceId)"
        :aria-current="palStore.SELECTED_PAL_ID == pal.InstanceId ? 'true' : undefined"
        :disabled="palStore.SELECTED_PAL_ID == pal.InstanceId || palStore.LOADING_FLAG">
        <PalPortrait :src="palStore.backendAssetUrl(`/image/pals/${pal.IconAccessKey}`)" alt="" size="2.5rem"
          :border-color="portraitBorder(pal)">
          <template #top-left>
            <img v-if="pal.IsBOSS" :src="palStore.backendAssetUrl('/image/ui/boss')" alt="" @error="$event.currentTarget.hidden = true">
            <img v-else-if="pal.IsRarePal" :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
          <template #top-right>
            <img v-if="pal.IsBOSS && pal.IsRarePal" :src="palStore.backendAssetUrl('/image/ui/rare')" alt="" @error="$event.currentTarget.hidden = true">
          </template>
        </PalPortrait>
        <span class="pal-copy">
          <strong class="pal-name">
            <span>{{ pal.DisplayName }}</span>
          </strong>
          <small>{{ palMetadata(pal) }}</small>
          <span class="sr-only">{{ palStatus(pal) }}</span>
        </span>
      </button>
    </div>
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-2);
  padding: var(--editor-space-3);
  border-bottom: 1px solid var(--editor-color-border);
}

.roster-header h2 {
  margin: 0;
  color: var(--editor-color-muted);
  font-size: .8rem;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.roster-actions {
  display: flex;
  gap: var(--editor-space-1);
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
