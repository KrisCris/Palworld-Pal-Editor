<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import NumberSliderField from '@/components/NumberSliderField.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  open: Boolean,
  items: { type: Array, default: () => [] },
  slot: { type: Object, default: null },
  equipment: Boolean,
})
const emit = defineEmits(['close', 'save'])
const palStore = usePalEditorStore()
const query = ref('')
const selectedId = ref(null)
const count = ref(1)
const searchInput = ref(null)
const optionElements = new Map()

const setOptionRef = (itemId, element) => {
  if (element) optionElements.set(itemId, element)
  else optionElements.delete(itemId)
}

watch(() => props.open, async value => {
  if (!value) return
  query.value = ''
  selectedId.value = props.slot?.static_id ?? null
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

const filteredItems = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return props.items
  return props.items.filter(item => `${item.Name} ${item.InternalName}`.toLocaleLowerCase().includes(needle))
})
const selectedItem = computed(() => palStore.ITEM_STATIC_DATA[selectedId.value])
const isStackable = computed(() => (selectedItem.value?.MaxStackCount || 1) > 1)
const maximum = computed(() => {
  if (props.equipment || !isStackable.value) return 1
  return palStore.HIDE_INVALID_OPTIONS
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
const save = () => emit('save', {
  itemId: selectedId.value,
  count: canAdjustCount.value
    ? Math.min(maximum.value, Math.max(1, Math.trunc(Number(count.value) || 1)))
    : 1,
})
const iconUrl = key => palStore.backendAssetUrl(`/image/items/${key}`)
</script>

<template>
  <div v-if="open" class="item-dialog-backdrop" role="presentation" @pointerdown.self="emit('close')">
    <section class="item-dialog" role="dialog" aria-modal="true" aria-labelledby="item-dialog-title">
      <header>
        <div>
          <small>{{ palStore.getTranslatedText('Inventory_Select_Hint') }}</small>
          <h2 id="item-dialog-title">{{ palStore.getTranslatedText('Inventory_Select_Item') }}</h2>
        </div>
        <button type="button" class="icon-button" @click="emit('close')" aria-label="Close">×</button>
      </header>

      <input ref="searchInput" v-model="query" class="item-search" type="search"
        :placeholder="palStore.getTranslatedText('Inventory_Search')">

      <div class="item-results">
        <button v-for="item in filteredItems" :key="item.InternalName"
          :ref="element => setOptionRef(item.InternalName, element)" type="button"
          class="item-option" :class="[`rarity-${Math.min(4, item.Rarity || 0)}`, { selected: selectedId === item.InternalName }]"
          @click="selectItem(item)">
          <span v-if="item.IconKey" class="option-icon" :class="{ layered: item.OverlayIconKey }">
            <img :src="iconUrl(item.IconKey)" alt="">
            <img v-if="item.OverlayIconKey" class="option-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
          </span>
          <span><strong>{{ item.Name }}</strong><small>{{ item.InternalName }}</small></span>
        </button>
        <p v-if="!filteredItems.length" class="empty-results">{{ palStore.getTranslatedText('Inventory_No_Results') }}</p>
      </div>

      <footer>
        <NumberSliderField v-if="canAdjustCount" v-model="count" class="quantity-control"
          :label="palStore.getTranslatedText('Inventory_Count')" :min="1" :max="maximum" :step="1" />
        <span v-else class="dialog-spacer"></span>
        <button type="button" class="danger-button" @click="emit('save', { itemId: null, count: 0 })">
          {{ palStore.getTranslatedText('Inventory_Clear') }}
        </button>
        <button type="button" class="primary-button" :disabled="!selectedId || palStore.LOADING_FLAG" @click="save">
          {{ palStore.getTranslatedText('Inventory_Apply') }}
        </button>
      </footer>
    </section>
  </div>
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
.item-dialog h2 { margin: .15rem 0 0; }
.item-dialog small { color: var(--editor-color-muted); }
.icon-button, .danger-button, .primary-button {
  border: 1px solid var(--editor-color-border);
  border-radius: .6rem;
  color: var(--editor-color-text);
  background: rgb(255 255 255 / .06);
  cursor: pointer;
}
.icon-button { width: 2.5rem; height: 2.5rem; font-size: 1.5rem; }
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
.danger-button { color: #fca5a5; }
.primary-button { border-color: var(--editor-color-focus); background: var(--editor-color-primary); }
button:disabled { opacity: .45; cursor: not-allowed; }
</style>
