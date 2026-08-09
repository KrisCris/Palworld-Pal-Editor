<script setup>
import { computed, nextTick, ref } from 'vue'

import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  slot: { type: Object, required: true },
  item: { type: Object, default: null },
  label: { type: String, required: true },
  editable: { type: Boolean, default: true },
  showName: { type: Boolean, default: false },
  showDurability: { type: Boolean, default: false },
  square: { type: Boolean, default: false },
})
const emit = defineEmits(['edit', 'clear'])
const palStore = usePalEditorStore()
const tooltipVisible = ref(false)
const tooltipRef = ref(null)
const tooltipPosition = ref({ left: '0px', top: '0px' })

const rarity = computed(() => Math.max(0, Math.min(4, props.item?.Rarity ?? 0)))
const rarityName = computed(() => palStore.getTranslatedText(`Inventory_Rarity_${rarity.value}`))
const itemType = computed(() => props.item
  ? palStore.getTranslatedText(`Inventory_Type_${props.item.TypeA}`)
  : '')
const iconUrl = key => palStore.backendAssetUrl(`/image/items/${key}`)

const placeTooltip = ({ clientX, clientY }) => {
  const rect = tooltipRef.value?.getBoundingClientRect()
  const width = rect?.width || 320
  const height = rect?.height || 280
  let left = clientX + 14
  let top = clientY + 14
  if (left + width + 12 > window.innerWidth) left = clientX - width - 14
  if (top + height + 12 > window.innerHeight) top = clientY - height - 14
  tooltipPosition.value = {
    left: `${Math.max(12, left)}px`,
    top: `${Math.max(12, top)}px`,
  }
}
const showTooltip = event => {
  if (!props.item) return
  tooltipVisible.value = true
  const point = { clientX: event.clientX, clientY: event.clientY }
  nextTick(() => placeTooltip(point))
}
const hideTooltip = () => { tooltipVisible.value = false }
</script>

<template>
  <div class="inventory-item-slot" :class="[`rarity-${rarity}`, { square, 'has-name': showName }]"
    @pointerenter="showTooltip" @pointermove="item && placeTooltip($event)" @pointerleave="hideTooltip">
    <button type="button" class="item-slot-button" :aria-label="label" @click="emit('edit')">
      <span v-if="item?.IconKey" class="item-icon" :class="{ layered: item.OverlayIconKey }">
        <img :src="iconUrl(item.IconKey)" alt="">
        <img v-if="item.OverlayIconKey" class="item-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
      </span>
      <span v-if="showName" class="slot-name">{{ label }}</span>
      <strong v-if="slot.count > 1" class="slot-count">{{ slot.count }}</strong>
      <span v-if="slot.warning" class="slot-warning">!</span>
      <span v-if="showDurability && slot.durability != null" class="durability">
        <i :style="{ width: `${Math.min(100, 100 * slot.durability / (item?.MaxDurability || 1))}%` }"></i>
      </span>
    </button>
    <button v-if="item && editable" type="button" class="slot-clear"
      :aria-label="palStore.getTranslatedText('Inventory_Clear')" @click.stop="emit('clear')">×</button>
  </div>

  <Teleport to="body">
    <aside v-if="tooltipVisible && item" ref="tooltipRef" class="item-hover-card"
      :class="`rarity-${rarity}`" :style="tooltipPosition" role="tooltip">
      <header>
        <strong>{{ item.Name }}</strong>
        <div class="tooltip-meta">
          <div class="tooltip-summary">
            <span>{{ itemType }}</span>
            <b>{{ rarityName }}</b>
          </div>
          <small>{{ item.InternalName }}</small>
        </div>
      </header>
      <section>
        <span class="tooltip-icon item-icon" :class="{ layered: item.OverlayIconKey }">
          <img :src="iconUrl(item.IconKey)" alt="">
          <img v-if="item.OverlayIconKey" class="item-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
        </span>
        <span class="tooltip-count">
          <small>{{ palStore.getTranslatedText('Inventory_Count') }}</small>
          <strong>{{ slot.count }}</strong>
        </span>
      </section>
      <p>{{ item.Description }}</p>
    </aside>
  </Teleport>
</template>

<style scoped>
.inventory-item-slot { position: relative; min-width: 0; }
.inventory-item-slot.square { aspect-ratio: 1; }
.item-slot-button {
  display: grid;
  width: 100%;
  height: 100%;
  min-width: 0;
  align-content: center;
  justify-items: center;
  gap: .2rem;
  padding: .28rem;
  border: 1px solid rgb(255 255 255 / .1);
  border-radius: .55rem;
  color: var(--editor-color-text);
  background: rgb(255 255 255 / .045);
  cursor: pointer;
  overflow: hidden;
}
.item-slot-button:hover, .item-slot-button:focus-visible { border-color: var(--editor-color-focus); transform: translateY(-1px); }
.item-icon { position: relative; display: grid; width: min(90%, 4rem); max-height: 90%; aspect-ratio: 1; place-items: center; }
.inventory-item-slot.square .item-slot-button { padding: 0; }
.inventory-item-slot.square .item-icon { width: 92%; height: auto; max-height: none; }
.inventory-item-slot.has-name .item-slot-button { grid-template-rows: minmax(0, 1fr) auto; align-content: stretch; justify-items: center; gap: .05rem; padding: .12rem .3rem .25rem; }
.inventory-item-slot.has-name .item-icon { width: 2.9rem; grid-row: 1; }
.inventory-item-slot.has-name .slot-name { grid-row: 2; font-size: .62rem; text-align: center; }
.item-icon img { width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 4px 5px rgb(0 0 0 / .38)); }
.item-icon.layered > img:first-child { position: absolute; inset: 0; }
.item-icon .item-icon-overlay { position: absolute; inset: 10%; width: 80%; height: 80%; }
.slot-name { width: 100%; overflow: hidden; color: var(--editor-color-muted); font-size: .62rem; text-overflow: ellipsis; white-space: nowrap; }
.slot-count { position: absolute; z-index: 1; right: .25rem; bottom: .15rem; font-size: .82rem; text-shadow: 0 1px 3px #000; }
.slot-warning { position: absolute; top: .3rem; left: .3rem; display: grid; width: 1.1rem; height: 1.1rem; place-items: center; border-radius: 50%; color: #1f1300; background: #fbbf24; font-size: .7rem; font-weight: 800; }
.slot-clear {
  position: absolute;
  z-index: 2;
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
.inventory-item-slot:hover .slot-clear, .slot-clear:focus-visible { opacity: 1; }
.slot-clear:hover { color: #fca5a5; }
.durability { position: absolute; right: 0; bottom: 0; left: 0; height: .2rem; overflow: hidden; border-radius: 0 0 .5rem .5rem; background: rgb(255 255 255 / .15); }
.durability i { display: block; height: 100%; background: #dbeafe; }
.rarity-1 .item-slot-button { background: linear-gradient(145deg, rgb(36 118 74 / .36), rgb(12 28 25 / .45)); }
.rarity-2 .item-slot-button { background: linear-gradient(145deg, rgb(33 101 166 / .4), rgb(13 27 47 / .48)); }
.rarity-3 .item-slot-button { background: linear-gradient(145deg, rgb(111 63 162 / .44), rgb(35 20 53 / .5)); }
.rarity-4 .item-slot-button { background: linear-gradient(145deg, rgb(158 104 24 / .5), rgb(52 35 14 / .52)); }
.item-hover-card {
  --rarity-accent: #9ca3af;
  --rarity-header: rgb(73 78 87 / .46);
  position: fixed;
  z-index: 2200;
  width: min(21rem, calc(100vw - 1.5rem));
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: .55rem;
  color: var(--editor-color-text);
  background: color-mix(in srgb, var(--editor-color-glass-surface) 94%, #0c1722);
  box-shadow: 0 18px 55px rgb(0 0 0 / .55);
  backdrop-filter: var(--editor-glass-filter);
  pointer-events: none;
}
.item-hover-card.rarity-1 { --rarity-accent: #4ade80; --rarity-header: rgb(24 94 55 / .5); }
.item-hover-card.rarity-2 { --rarity-accent: #38bdf8; --rarity-header: rgb(21 82 117 / .52); }
.item-hover-card.rarity-3 { --rarity-accent: #c084fc; --rarity-header: rgb(89 46 128 / .52); }
.item-hover-card.rarity-4 { --rarity-accent: #facc15; --rarity-header: rgb(120 82 17 / .54); }
.item-hover-card header { display: grid; gap: .35rem; padding: .75rem .85rem; border-bottom: 2px solid var(--rarity-accent); background: linear-gradient(135deg, var(--rarity-header), rgb(8 18 26 / .8)); }
.item-hover-card header > strong { font-size: 1.08rem; }
.tooltip-meta { display: grid; min-width: 0; gap: .15rem; }
.tooltip-summary { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: .75rem; color: var(--editor-color-muted); font-size: .78rem; }
.tooltip-meta > small { overflow: hidden; color: color-mix(in srgb, var(--editor-color-muted) 80%, transparent); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .65rem; text-overflow: ellipsis; white-space: nowrap; }
.item-hover-card header b { padding: .15rem .5rem; border-right: 1px solid currentColor; border-left: 1px solid currentColor; color: var(--rarity-accent); }
.item-hover-card section { position: relative; display: flex; min-height: 8.5rem; align-items: center; padding: .75rem 1.15rem; background: rgb(255 255 255 / .05); }
.item-hover-card .tooltip-icon { width: 7rem; }
.tooltip-count { position: absolute; right: .85rem; bottom: .7rem; display: flex; min-width: 7.5rem; align-items: center; justify-content: space-between; gap: 1rem; padding: .35rem .55rem; border: 1px solid var(--editor-color-border); background: rgb(7 16 23 / .68); }
.tooltip-count small { color: var(--editor-color-muted); }
.item-hover-card p { margin: 0; padding: .75rem .85rem; color: #d5e1ea; font-size: .83rem; line-height: 1.45; white-space: pre-line; }
</style>
