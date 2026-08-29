<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import InventoryItemSlot from '@/components/InventoryItemSlot.vue'
import ItemSelectDialog from '@/components/ItemSelectDialog.vue'
import { useCatalogsStore } from '@/stores/catalogs'
import { usePalEditorStore } from '@/stores/paleditor'
import { usePlayersStore } from '@/stores/players'
import { useRostersStore } from '@/stores/rosters'

const catalogsStore = useCatalogsStore()
const palStore = usePalEditorStore()
const playersStore = usePlayersStore()
const rostersStore = useRostersStore()
const bagTab = ref('common')
const editing = ref(null)
const inventoryEditor = ref(null)
const inventoryLayout = ref(null)
const bagPanel = ref(null)
const bagScroll = ref(null)
const bagGrid = ref(null)
const bagColumnCount = ref(6)
const bagPanelWidth = ref('auto')
let layoutObserver
let layoutFrame = 0
let observedLayoutWidth = 0
const armorLabels = ['Inventory_Head', 'Inventory_Body', 'Inventory_Accessory', 'Inventory_Accessory', 'Inventory_Shield', 'Inventory_Glider', 'Inventory_Accessory', 'Inventory_Accessory', 'Inventory_Sphere_Module']
const armorGroups = ['Head', 'Body', 'Accessory', 'Accessory', 'Shield', 'Glider', 'Accessory', 'Accessory', 'SphereModule']

watch(() => rostersStore.activePlayerUid, () => palStore.loadPlayerInventory(), { immediate: true })

const containers = computed(() => playersStore.inventory?.containers || {})
const currentBag = computed(() => containers.value[bagTab.value])
const armorSlots = computed(() => containers.value.armor?.slots || [])
const primaryArmorSlots = computed(() => armorSlots.value.filter(slot => [0, 1, 4, 5, 8].includes(slot.slot_index)))
const accessorySlots = computed(() => armorSlots.value.filter(slot => [2, 3, 6, 7].includes(slot.slot_index)))
const itemFor = slot => catalogsStore.itemsByName[slot?.static_id]
const detailsItemFor = slot => catalogsStore.itemsByName[slot?.effective_static_id] || itemFor(slot)
const slotName = slot => itemFor(slot)?.Name || slot?.static_id || palStore.getTranslatedText('Inventory_Empty')
const armorLabel = slot => palStore.getTranslatedText(armorLabels[slot.slot_index] || 'Inventory_Accessory')
const isEditable = kind => containers.value[kind]?.editable !== false
const candidates = computed(() => {
  if (!editing.value) return []
  const { kind, slot } = editing.value
  const required = kind === 'armor' ? armorGroups[slot.slot_index]
    : kind === 'weapons' ? 'Weapon'
      : kind === 'food' ? 'Food'
        : kind === 'key_items' ? 'KeyItem' : null
  return catalogsStore.items.filter(item => {
    if (!item.Legal || item.Disabled || item.MonsterOnly || item.Group === 'None' || item.DynamicType === 'egg') return false
    if (kind === 'common') return item.Group !== 'KeyItem'
    return item.Group === required
  })
})
const openSlot = (kind, slot) => {
  if (containers.value[kind]?.editable === false) return
  editing.value = { kind, slot }
}
const applySlot = async ({ itemId, count }) => {
  const target = editing.value
  if (!target) return
  if (await palStore.patchInventorySlot(target.kind, target.slot.slot_index, itemId, count)) editing.value = null
}
const clearSlot = (kind, slot) => palStore.patchInventorySlot(kind, slot.slot_index, null, 0)

const updateBagLayout = () => {
  if (!inventoryLayout.value || !bagPanel.value || !bagScroll.value || !bagGrid.value) return
  const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
  const layoutStyle = getComputedStyle(inventoryLayout.value)
  const panelStyle = getComputedStyle(bagPanel.value)
  const scrollStyle = getComputedStyle(bagScroll.value)
  const gridStyle = getComputedStyle(bagGrid.value)
  const layoutWidth = inventoryLayout.value.clientWidth
  const layoutGap = parseFloat(layoutStyle.columnGap) || 0
  const equipmentMinimum = 27 * rootFontSize
  const preferredWidth = Math.min(layoutWidth * .6, layoutWidth - layoutGap - equipmentMinimum)
  const slotSize = 4.5 * rootFontSize
  const slotGap = parseFloat(gridStyle.columnGap) || 0
  const panelChrome = (parseFloat(panelStyle.borderLeftWidth) || 0)
    + (parseFloat(panelStyle.borderRightWidth) || 0)
    + (parseFloat(scrollStyle.paddingLeft) || 0)
    + (parseFloat(scrollStyle.paddingRight) || 0)
  const columns = Math.max(1, Math.floor((preferredWidth - panelChrome + slotGap) / (slotSize + slotGap)))
  const panelWidth = `${panelChrome + columns * slotSize + (columns - 1) * slotGap}px`
  if (bagColumnCount.value !== columns) bagColumnCount.value = columns
  if (bagPanelWidth.value !== panelWidth) bagPanelWidth.value = panelWidth
}

const scheduleBagLayout = () => {
  cancelAnimationFrame(layoutFrame)
  layoutFrame = requestAnimationFrame(() => {
    layoutFrame = 0
    updateBagLayout()
  })
}

onMounted(async () => {
  await nextTick()
  scheduleBagLayout()
  layoutObserver = new ResizeObserver(entries => {
    const width = entries[0]?.contentRect.width || 0
    if (Math.abs(width - observedLayoutWidth) < .5) return
    observedLayoutWidth = width
    scheduleBagLayout()
  })
  layoutObserver.observe(inventoryEditor.value)
})
onBeforeUnmount(() => {
  layoutObserver?.disconnect()
  cancelAnimationFrame(layoutFrame)
})
</script>

<template>
  <section ref="inventoryEditor" class="inventory-editor">
    <div ref="inventoryLayout" class="inventory-layout" :style="{ '--bag-panel-width': bagPanelWidth, '--bag-columns': bagColumnCount }">
      <section ref="bagPanel" class="inventory-panel bag-panel">
        <nav class="bag-tabs" :aria-label="palStore.getTranslatedText('Inventory_Containers')">
          <button type="button" :class="{ active: bagTab === 'common' }" @click="bagTab = 'common'">{{ palStore.getTranslatedText('Inventory_Backpack') }}</button>
          <button type="button" :class="{ active: bagTab === 'key_items' }" @click="bagTab = 'key_items'">{{ palStore.getTranslatedText('Inventory_Key_Items') }}</button>
        </nav>
        <div ref="bagScroll" class="bag-scroll">
          <p v-if="currentBag?.warning" class="container-warning">{{ currentBag.warning }}</p>
          <div ref="bagGrid" class="slot-grid slot-grid--bag">
            <InventoryItemSlot v-for="slot in currentBag?.slots" :key="slot.slot_index"
              :slot="slot" :item="itemFor(slot)" :details-item="detailsItemFor(slot)" :label="slotName(slot)" :editable="isEditable(bagTab)" square
              @edit="openSlot(bagTab, slot)" @clear="clearSlot(bagTab, slot)" />
          </div>
        </div>
      </section>

      <section class="inventory-panel equipment-panel">
        <header class="panel-heading">
          <h2>{{ palStore.getTranslatedText('Inventory_Equipment') }}</h2>
          <span v-if="playersStore.inventory?.warnings?.length" class="warning-chip" :title="playersStore.inventory.warnings.join('\n')">!</span>
        </header>

        <div v-if="!playersStore.inventory" class="inventory-loading">{{ palStore.getTranslatedText('Inventory_Loading') }}</div>
        <div v-else class="equipment-layout">
          <section class="equipment-group weapons-group">
            <h3>{{ palStore.getTranslatedText('Inventory_Weapons') }}</h3>
            <div class="slot-grid slot-grid--equipment">
              <InventoryItemSlot v-for="slot in containers.weapons?.slots" :key="slot.slot_index"
                :slot="slot" :item="itemFor(slot)" :details-item="detailsItemFor(slot)" :label="slotName(slot)" :editable="isEditable('weapons')"
                show-name show-durability @edit="openSlot('weapons', slot)" @clear="clearSlot('weapons', slot)" />
            </div>
          </section>

          <section class="equipment-group armor-group">
            <h3>{{ palStore.getTranslatedText('Inventory_Armor') }}</h3>
            <div class="armor-slots">
              <div class="armor-main-slots">
                <div v-for="slot in primaryArmorSlots" :key="slot.slot_index" class="equipment-slot-field">
                  <span>{{ armorLabel(slot) }}</span>
                  <InventoryItemSlot :slot="slot" :item="itemFor(slot)" :details-item="detailsItemFor(slot)" :label="slotName(slot)"
                    :editable="isEditable('armor')" show-name @edit="openSlot('armor', slot)" @clear="clearSlot('armor', slot)" />
                </div>
              </div>
              <section class="accessory-group">
                <span>{{ palStore.getTranslatedText('Inventory_Accessories') }}</span>
                <div class="accessory-grid">
                  <div v-for="slot in accessorySlots" :key="slot.slot_index" class="equipment-slot-field accessory-slot-field">
                    <InventoryItemSlot :slot="slot" :item="itemFor(slot)" :details-item="detailsItemFor(slot)" :label="slotName(slot)"
                      :editable="isEditable('armor')" show-name @edit="openSlot('armor', slot)" @clear="clearSlot('armor', slot)" />
                  </div>
                </div>
              </section>
            </div>
          </section>

          <section class="equipment-group food-group">
            <h3>{{ palStore.getTranslatedText('Inventory_Food') }}</h3>
            <div class="slot-grid slot-grid--food">
              <InventoryItemSlot v-for="slot in containers.food?.slots" :key="slot.slot_index"
                :slot="slot" :item="itemFor(slot)" :details-item="detailsItemFor(slot)" :label="slotName(slot)" :editable="isEditable('food')"
                @edit="openSlot('food', slot)" @clear="clearSlot('food', slot)" />
            </div>
          </section>
        </div>
      </section>
    </div>

    <ItemSelectDialog :open="Boolean(editing)" :items="candidates" :slot="editing?.slot"
      :equipment="editing?.kind === 'weapons' || editing?.kind === 'armor'" @close="editing = null" @save="applySlot" />
  </section>
</template>

<style scoped>
.inventory-editor { --inventory-slot-height: 4.5rem; display: grid; min-height: 0; height: 100%; color: var(--editor-color-text); }
.inventory-layout {
  display: grid;
  grid-template-columns: var(--bag-panel-width) minmax(27rem, 1fr);
  min-height: 0;
  height: 100%;
  gap: var(--editor-space-3);
  align-items: stretch;
}
.inventory-layout > .inventory-panel { min-height: 0; height: 100%; }
.inventory-panel {
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: var(--editor-color-glass-surface);
  box-shadow: var(--editor-glass-shadow);
  backdrop-filter: var(--editor-glass-filter);
}
.equipment-panel { overflow: hidden; padding: .65rem; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: .5rem; }
.panel-heading h2 { margin: 0; font-size: 1.05rem; }
.equipment-group h3 { margin: 0; font-size: .86rem; }
.warning-chip, .slot-warning { display: grid; place-items: center; border-radius: 50%; color: #1f1300; background: #fbbf24; font-weight: 800; }
.warning-chip { width: 1.7rem; height: 1.7rem; }
.equipment-layout { display: grid; grid-template-columns: 1fr; gap: .5rem; height: calc(100% - 2rem); overflow: auto; }
.equipment-group { min-width: 0; padding: .55rem; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); background: rgb(0 0 0 / .13); }
.slot-grid { display: grid; gap: .35rem; margin-top: .45rem; }
.slot-grid--equipment { grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); }
.slot-grid--food { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.armor-slots { display: grid; gap: .55rem; margin-top: .45rem; }
.armor-main-slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: .35rem; align-content: start; }
.equipment-slot-field { display: grid; gap: .2rem; min-width: 0; color: var(--editor-color-muted); font-size: .62rem; }
.equipment-slot-field > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.accessory-group { display: grid; align-content: start; gap: .25rem; padding-top: .45rem; border-top: 1px solid var(--editor-color-border); color: var(--editor-color-muted); font-size: .68rem; }
.accessory-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .35rem; }
.bag-panel { overflow: hidden; }
.bag-tabs { display: grid; grid-template-columns: 1fr 1fr; padding: .55rem; border-bottom: 1px solid var(--editor-color-border); }
.bag-tabs button { padding: .75rem; border: 0; border-radius: .55rem; color: var(--editor-color-muted); background: transparent; cursor: pointer; }
.bag-tabs button.active { color: var(--editor-color-text); background: var(--editor-color-primary); }
.bag-scroll { height: calc(100% - 4rem); overflow: auto; padding: var(--editor-space-3); }
.slot-grid--bag { grid-template-columns: repeat(var(--bag-columns), var(--inventory-slot-height)); margin-top: 0; }
.equipment-panel :deep(.inventory-item-slot) { height: var(--inventory-slot-height); }
.container-warning, .inventory-loading { color: var(--editor-color-muted); }
@container (max-width: 50rem) {
  .inventory-layout { grid-template-columns: 1fr; height: auto; }
  .inventory-layout > .bag-panel { order: 1; height: min(42rem, 70vh); min-height: 30rem; }
  .inventory-layout > .equipment-panel { order: 2; height: auto; min-height: 0; }
  .equipment-layout { height: auto; overflow: visible; }
  .slot-grid--bag { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .slot-grid--bag :deep(.inventory-item-slot.square) { height: var(--inventory-slot-height); aspect-ratio: auto; }
  .slot-grid--bag :deep(.inventory-item-slot.square .item-icon) { width: 4rem; height: 4rem; max-width: 92%; max-height: 92%; }
}
</style>
