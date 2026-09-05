<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import ItemHoverCard from '@/components/ItemHoverCard.vue'
import NumberSliderField from '@/components/modules/NumberSliderField.vue'
import PalGearBadge from '@/components/PalGearBadge.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { closeDisclosureOnOutsidePointer } from '@/components/modules/search-select'
import { readStorage, writeStorage } from '@/services/backend-connection'
import { useCatalogsStore } from '@/stores/catalogs'
import { useAppStore } from '@/stores/app'
import { useBackendStore } from '@/stores/backend'

const TYPE_FILTER_STORAGE_KEY = 'PAL_ITEM_FILTER_TYPES'
const RARITY_FILTER_STORAGE_KEY = 'PAL_ITEM_FILTER_RARITIES'
const TYPE_ICONS = Object.freeze({
  Accessory: 'Accessory_AT',
  Ammo: 'AssaultRifleBullet',
  Armor: 'AncientArmor',
  Blueprint: 'Blueprint',
  CaptureItemModifier: 'SphereModule_Homing',
  Consume: 'AffectionFruit_01',
  Essential: 'AdditionalInventory_001',
  Food: 'BLT',
  Glider: 'Glider_Good',
  Material: 'AIcore',
  SpecialWeapon: 'CapturePrism',
  Weapon: 'AssaultRifle_Default',
})
const readStoredArray = key => {
  try {
    const value = JSON.parse(readStorage(localStorage, key) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

const props = defineProps({
  open: Boolean,
  items: { type: Array, default: () => [] },
  slot: { type: Object, default: null },
  equipment: Boolean,
})
const emit = defineEmits(['close', 'save'])
const catalogsStore = useCatalogsStore()
const appStore = useAppStore()
const backend = useBackendStore()
const query = ref('')
const selectedTypes = ref(readStoredArray(TYPE_FILTER_STORAGE_KEY).filter(value => typeof value === 'string'))
const selectedRarities = ref(readStoredArray(RARITY_FILTER_STORAGE_KEY)
  .map(Number).filter(value => Number.isInteger(value) && value >= 0 && value <= 4))
const selectedId = ref(null)
const pinnedItemId = ref(null)
const count = ref(1)
const searchInput = ref(null)
const filterMenu = ref(null)
const optionElements = new Map()
const hoveredItem = ref(null)
const hoverPoint = ref({ clientX: 0, clientY: 0 })
let hoverTimer = null

const setOptionRef = (itemId, element) => {
  if (element) optionElements.set(itemId, element)
  else optionElements.delete(itemId)
}

watch(() => props.open, async value => {
  clearHover()
  if (!value) {
    pinnedItemId.value = null
    return
  }
  query.value = ''
  selectedId.value = props.slot?.static_id ?? null
  pinnedItemId.value = selectedId.value
    && !filteredItems.value.some(item => item.InternalName === selectedId.value)
    ? selectedId.value
    : null
  count.value = props.equipment ? 1 : Math.max(1, props.slot?.count || 1)
  await nextTick()
  const currentOption = optionElements.get(selectedId.value)
  if (currentOption) {
    currentOption.focus({ preventScroll: true })
    currentOption.scrollIntoView({ block: 'center' })
  } else {
    searchInput.value?.focus()
  }
})

const availableTypes = computed(() => [...new Set(props.items.map(item => item.TypeA).filter(Boolean))]
  .sort((left, right) => appStore.getTranslatedText(`Inventory_Type_${left}`)
    .localeCompare(appStore.getTranslatedText(`Inventory_Type_${right}`))))
const availableRarities = computed(() => [...new Set(props.items.map(item => Math.max(0, Math.min(4, item.Rarity || 0))))]
  .sort((left, right) => left - right))
const effectiveTypes = computed(() => selectedTypes.value.filter(type => availableTypes.value.includes(type)))
const effectiveRarities = computed(() => selectedRarities.value.filter(rarity => availableRarities.value.includes(rarity)))
const activeFilterCount = computed(() => effectiveTypes.value.length + effectiveRarities.value.length)
const filteredItems = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase()
  return props.items.filter(item => (
    (!needle || `${item.Name} ${item.InternalName}`.toLocaleLowerCase().includes(needle))
    && (!effectiveTypes.value.length || effectiveTypes.value.includes(item.TypeA))
    && (!effectiveRarities.value.length
      || effectiveRarities.value.includes(Math.max(0, Math.min(4, item.Rarity || 0))))
  ))
})
const visibleItems = computed(() => {
  const pinned = props.items.find(item => item.InternalName === pinnedItemId.value)
  return !pinned
    ? filteredItems.value
    : [pinned, ...filteredItems.value.filter(item => item.InternalName !== pinned.InternalName)]
})
const typeIcon = type => TYPE_ICONS[type]
const toggleType = type => {
  selectedTypes.value = selectedTypes.value.includes(type)
    ? selectedTypes.value.filter(current => current !== type)
    : [...selectedTypes.value, type]
}
const toggleRarity = rarity => {
  selectedRarities.value = selectedRarities.value.includes(rarity)
    ? selectedRarities.value.filter(current => current !== rarity)
    : [...selectedRarities.value, rarity]
}
const clearFilters = () => {
  selectedTypes.value = []
  selectedRarities.value = []
}
watch(selectedTypes, value => writeStorage(localStorage, TYPE_FILTER_STORAGE_KEY, JSON.stringify(value)), { deep: true })
watch(selectedRarities, value => writeStorage(localStorage, RARITY_FILTER_STORAGE_KEY, JSON.stringify(value)), { deep: true })
const selectedItem = computed(() => catalogsStore.itemsByName[selectedId.value])
const isStackable = computed(() => (selectedItem.value?.MaxStackCount || 1) > 1)
const maximum = computed(() => {
  if (props.equipment || !isStackable.value) return 1
  return appStore.HIDE_INVALID_OPTIONS
    ? Math.min(999999, Math.max(1, selectedItem.value?.MaxStackCount || 1))
    : 999999
})
const canAdjustCount = computed(() => Boolean(selectedId.value) && isStackable.value)
watch([count, maximum], ([value, limit]) => {
  const normalized = Math.min(limit, Math.max(1, Math.trunc(Number(value) || 1)))
  if (value !== normalized) count.value = normalized
})
const selectItem = item => {
  selectedId.value = item.InternalName
  count.value = item.InternalName === props.slot?.static_id
    ? Math.min(maximum.value, Math.max(1, props.slot?.count || 1))
    : 1
}
function clearHover() {
  if (hoverTimer != null) window.clearTimeout(hoverTimer)
  hoverTimer = null
  hoveredItem.value = null
}
const startHover = (event, item) => {
  clearHover()
  hoverPoint.value = { clientX: event.clientX, clientY: event.clientY }
  hoverTimer = window.setTimeout(() => {
    hoveredItem.value = item
    hoverTimer = null
  }, 500)
}
const moveHover = event => {
  if (hoveredItem.value) hoverPoint.value = { clientX: event.clientX, clientY: event.clientY }
}
const closeFilterMenuOnOutsidePointer = event => closeDisclosureOnOutsidePointer(filterMenu.value, event.target)
onMounted(() => window.addEventListener('pointerdown', closeFilterMenuOnOutsidePointer))
onBeforeUnmount(() => {
  clearHover()
  window.removeEventListener('pointerdown', closeFilterMenuOnOutsidePointer)
})
const save = () => emit('save', {
  itemId: selectedId.value,
  count: canAdjustCount.value
    ? Math.min(maximum.value, Math.max(1, Math.trunc(Number(count.value) || 1)))
    : 1,
})
const iconUrl = key => backend.backendAssetUrl(`/image/items/${key}`)
</script>

<template>
  <!-- Every other overlay in this app teleports to the body, and this one has to
  for the same reason: `.editor-canvas` sets `isolation: isolate`, so a backdrop
  left inside it opens a stacking context the roster rails -- siblings of the
  canvas, not descendants -- sit above however high its z-index goes. -->
  <Teleport to="body">
    <div v-if="open" class="item-dialog-backdrop" role="presentation" @pointerdown.self="emit('close')">
      <section class="item-dialog" role="dialog" aria-modal="true" aria-labelledby="item-dialog-title">
        <header>
          <div>
            <small>{{ appStore.getTranslatedText('Inventory_Select_Hint') }}</small>
            <h2 id="item-dialog-title">{{ appStore.getTranslatedText('Inventory_Select_Item') }}</h2>
          </div>
          <div class="dialog-header-actions">
            <details ref="filterMenu" class="item-filter-menu">
              <summary class="icon-button filter-button" :class="{ 'is-active': activeFilterCount > 0 }"
                :title="appStore.getTranslatedText('Inventory_Filter')"
                :aria-label="appStore.getTranslatedText('Inventory_Filter')">
                <UiIcon name="filter" />
                <span v-if="activeFilterCount" class="filter-count">{{ activeFilterCount }}</span>
              </summary>
              <div class="item-filter-popover editor-glass-surface">
                <fieldset>
                  <legend>{{ appStore.getTranslatedText('Inventory_Filter_Type') }}</legend>
                  <div class="type-filter-grid">
                    <button v-for="type in availableTypes" :key="type" type="button" class="filter-option type-filter-option"
                      :class="{ 'is-active': selectedTypes.includes(type) }"
                      :aria-pressed="selectedTypes.includes(type)"
                      @click="toggleType(type)">
                      <img v-if="typeIcon(type)" :src="iconUrl(typeIcon(type))" alt=""
                        @error="$event.currentTarget.hidden = true">
                      <span>{{ appStore.getTranslatedText(`Inventory_Type_${type}`) }}</span>
                    </button>
                  </div>
                </fieldset>
                <fieldset>
                  <legend>{{ appStore.getTranslatedText('Inventory_Filter_Rarity') }}</legend>
                  <div class="rarity-filter-grid">
                    <button v-for="rarity in availableRarities" :key="rarity" type="button"
                      class="filter-option rarity-filter-option" :class="[`rarity-${rarity}`, { 'is-active': selectedRarities.includes(rarity) }]"
                      :aria-pressed="selectedRarities.includes(rarity)"
                      @click="toggleRarity(rarity)">
                      <i></i>
                      <span>{{ appStore.getTranslatedText(`Inventory_Rarity_${rarity}`) }}</span>
                    </button>
                  </div>
                </fieldset>
                <button type="button" class="clear-filter-button" :disabled="!selectedTypes.length && !selectedRarities.length"
                  @click="clearFilters">
                  <UiIcon name="close" />
                  {{ appStore.getTranslatedText('Inventory_Filter_Clear') }}
                </button>
              </div>
            </details>
            <button type="button" class="icon-button" @click="emit('close')" aria-label="Close">×</button>
          </div>
        </header>

        <input ref="searchInput" v-model="query" class="item-search" type="search"
          :placeholder="appStore.getTranslatedText('Inventory_Search')">

        <div class="item-results">
          <button v-for="item in visibleItems" :key="item.InternalName"
            :ref="element => setOptionRef(item.InternalName, element)" type="button"
            class="item-option" :class="[`rarity-${Math.min(4, item.Rarity || 0)}`, { selected: selectedId === item.InternalName }]"
            @pointerenter="startHover($event, item)" @pointermove="moveHover" @pointerleave="clearHover"
            @click="selectItem(item)">
            <span v-if="item.IconKey" class="option-icon" :class="{ layered: item.OverlayIconKey }">
              <img :src="iconUrl(item.IconKey)" alt="">
              <img v-if="item.OverlayIconKey" class="option-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
              <PalGearBadge :item="item" />
            </span>
            <span><strong>{{ item.Name }}</strong><small>{{ item.InternalName }}</small></span>
          </button>
          <p v-if="!visibleItems.length" class="empty-results">{{ appStore.getTranslatedText('Inventory_No_Results') }}</p>
        </div>

        <footer>
          <NumberSliderField v-if="canAdjustCount" v-model="count" class="quantity-control"
            :label="appStore.getTranslatedText('Inventory_Count')" :min="1" :max="maximum" :step="1" />
          <span v-else class="dialog-spacer"></span>
          <button type="button" class="editor-button editor-button--danger danger-button"
            @click="emit('save', { itemId: null, count: 0 })">
            {{ appStore.getTranslatedText('Inventory_Clear') }}
          </button>
          <button type="button" class="primary-button" :disabled="!selectedId" @click="save">
            {{ appStore.getTranslatedText('Inventory_Apply') }}
          </button>
        </footer>
      </section>
      <ItemHoverCard v-if="hoveredItem" :item="hoveredItem"
        :count="hoveredItem.InternalName === selectedId ? count : null"
        :client-x="hoverPoint.clientX" :client-y="hoverPoint.clientY" />
    </div>
  </Teleport>
</template>

<style scoped>
.item-dialog-backdrop {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(3 7 18 / .72);
  backdrop-filter: blur(10px);
}
.item-dialog {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  width: min(62rem, 94vw);
  max-height: min(48rem, 90vh);
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-glass-surface) 92%, #101827);
  box-shadow: 0 24px 80px rgb(0 0 0 / .52);
  backdrop-filter: var(--editor-glass-filter);
}
.item-dialog header, .item-dialog footer { display: flex; align-items: center; gap: .75rem; }
.item-dialog header { justify-content: space-between; }
.dialog-header-actions { display: flex; align-items: center; gap: .55rem; }
.item-dialog h2 { margin: .15rem 0 0; }
.item-dialog small { color: var(--editor-color-muted); }
.icon-button, .primary-button {
  border: 1px solid var(--editor-color-border);
  border-radius: .6rem;
  color: var(--editor-color-text);
  background: rgb(255 255 255 / .06);
  cursor: pointer;
}
.icon-button { position: relative; display: grid; width: 2.5rem; height: 2.5rem; padding: 0; place-items: center; font-size: 1.5rem; list-style: none; }
.icon-button::-webkit-details-marker { display: none; }
.filter-button { color: var(--editor-color-muted); background: var(--editor-color-control); }
.filter-button:hover { color: var(--editor-color-text); background: var(--editor-color-control-hover); }
.filter-button.is-active { border-color: var(--editor-color-primary); color: var(--editor-color-background); background: var(--editor-color-primary); }
.filter-button .ui-icon { font-size: 1rem; }
.filter-count { position: absolute; top: -.3rem; right: -.3rem; display: grid; min-width: 1rem; height: 1rem; place-items: center; padding: 0 .2rem; border-radius: 999px; color: var(--editor-color-background); background: var(--editor-color-primary); font-size: .6rem; font-weight: 700; }
.filter-button.is-active .filter-count { color: var(--editor-color-primary); background: var(--editor-color-text); }
.item-filter-menu { position: relative; }
.item-filter-popover {
  position: absolute;
  z-index: 40;
  top: calc(100% + .55rem);
  right: 0;
  display: grid;
  width: min(34rem, calc(100vw - 3rem));
  gap: .85rem;
  padding: .9rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  box-shadow: var(--editor-shadow-compact);
}
.item-filter-popover fieldset { display: grid; gap: .45rem; margin: 0; padding: 0; border: 0; }
.item-filter-popover legend { margin-bottom: .35rem; color: var(--editor-color-muted); font-size: .72rem; }
.type-filter-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .4rem; }
.rarity-filter-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .4rem; }
.filter-option {
  min-width: 0;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-muted);
  background: var(--editor-color-control);
  cursor: pointer;
}
.filter-option:hover { color: var(--editor-color-text); background: var(--editor-color-control-hover); }
.filter-option.is-active { border-color: var(--editor-color-primary); color: var(--editor-color-primary); background: color-mix(in srgb, var(--editor-color-primary) 15%, var(--editor-color-control)); }
.type-filter-option { display: grid; min-height: 4rem; place-items: center; gap: .15rem; padding: .35rem; font-size: .65rem; }
.type-filter-option img { width: 2rem; height: 2rem; object-fit: contain; filter: drop-shadow(0 2px 3px rgb(0 0 0 / .35)); }
.type-filter-option span, .rarity-filter-option span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rarity-filter-option { --rarity-filter-color: #9ca3af; display: grid; min-height: 2.65rem; place-items: center; gap: .2rem; padding: .35rem; font-size: .65rem; }
.rarity-filter-option.rarity-1 { --rarity-filter-color: #4ade80; }
.rarity-filter-option.rarity-2 { --rarity-filter-color: #38bdf8; }
.rarity-filter-option.rarity-3 { --rarity-filter-color: #c084fc; }
.rarity-filter-option.rarity-4 { --rarity-filter-color: #facc15; }
.rarity-filter-option i { width: .8rem; height: .8rem; border-radius: .2rem; background: var(--rarity-filter-color); box-shadow: 0 0 .45rem color-mix(in srgb, var(--rarity-filter-color) 55%, transparent); transform: rotate(45deg); }
.rarity-filter-option.is-active { border-color: var(--rarity-filter-color); color: var(--rarity-filter-color); background: color-mix(in srgb, var(--rarity-filter-color) 16%, var(--editor-color-control)); }
.clear-filter-button { display: flex; min-height: 2.25rem; align-items: center; justify-content: center; gap: .35rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); color: var(--editor-color-text); background: var(--editor-color-control); cursor: pointer; }
.clear-filter-button:hover { background: var(--editor-color-control-hover); }
.item-search {
  border: 1px solid var(--editor-color-border);
  border-radius: .65rem;
  color: var(--editor-color-text);
  background: rgb(0 0 0 / .24);
}
.item-search { padding: .8rem 1rem; font-size: 1rem; }
.item-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: .55rem;
  min-height: 12rem;
  overflow: auto;
}
.item-option {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: .65rem;
  padding: .55rem;
  border: 1px solid transparent;
  border-radius: .65rem;
  color: var(--editor-color-text);
  text-align: left;
  background: rgb(255 255 255 / .045);
  cursor: pointer;
}
.item-option:hover, .item-option.selected { border-color: var(--editor-color-focus); }
.item-option.rarity-1 { background: linear-gradient(145deg, rgb(36 118 74 / .25), rgb(255 255 255 / .035)); }
.item-option.rarity-2 { background: linear-gradient(145deg, rgb(33 101 166 / .28), rgb(255 255 255 / .035)); }
.item-option.rarity-3 { background: linear-gradient(145deg, rgb(111 63 162 / .3), rgb(255 255 255 / .035)); }
.item-option.rarity-4 { background: linear-gradient(145deg, rgb(158 104 24 / .34), rgb(255 255 255 / .035)); }
.item-option.selected { box-shadow: inset 0 0 0 1px var(--editor-color-focus); }
.option-icon { position: relative; display: grid; width: 3rem; height: 3rem; flex: 0 0 auto; place-items: center; }
.option-icon img { width: 100%; height: 100%; object-fit: contain; }
.option-icon.layered > img:first-child { position: absolute; inset: 0; }
.option-icon .option-icon-overlay { position: absolute; inset: 10%; width: 80%; height: 80%; }
.item-option span { display: grid; min-width: 0; }
.item-option strong, .item-option small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-results { color: var(--editor-color-muted); }
.dialog-spacer { flex: 1; }
.quantity-control { min-width: 16rem; flex: 1 1 24rem; }
.danger-button, .primary-button { padding: .65rem 1rem; }
.primary-button { border-color: var(--editor-color-focus); background: var(--editor-color-primary); }
button:disabled { opacity: .45; cursor: not-allowed; }
@media (max-width: 38rem) {
  .type-filter-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .rarity-filter-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
