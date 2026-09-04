<script setup>
import { computed, ref } from 'vue'

import ItemHoverCard from '@/components/ItemHoverCard.vue'
import PalGearBadge from '@/components/PalGearBadge.vue'
import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  slot: { type: Object, required: true },
  item: { type: Object, default: null },
  detailsItem: { type: Object, default: null },
  label: { type: String, required: true },
  editable: { type: Boolean, default: true },
  showName: { type: Boolean, default: false },
  showDurability: { type: Boolean, default: false },
  square: { type: Boolean, default: false },
})
const emit = defineEmits(['edit', 'clear', 'repair'])
const palStore = usePalEditorStore()
const tooltipVisible = ref(false)
const tooltipPoint = ref({ clientX: 0, clientY: 0 })

const rarity = computed(() => Math.max(0, Math.min(4, props.item?.Rarity ?? 0)))
// The game data leaves MaxDurability at 0 for some real items -- grappling guns,
// sphere launchers -- so there is no maximum to restore and no repair to offer.
const maxDurability = computed(
  () => props.detailsItem?.MaxDurability || props.item?.MaxDurability || 0)
const repairable = computed(() => props.editable
  && props.slot.durability != null
  && maxDurability.value > 0
  && props.slot.durability < maxDurability.value)
const iconUrl = key => palStore.backendAssetUrl(`/image/items/${key}`)

const showTooltip = event => {
  if (!props.item) return
  tooltipPoint.value = { clientX: event.clientX, clientY: event.clientY }
  tooltipVisible.value = true
}
const moveTooltip = event => { tooltipPoint.value = { clientX: event.clientX, clientY: event.clientY } }
const hideTooltip = () => { tooltipVisible.value = false }
</script>

<template>
  <div class="inventory-item-slot" :class="[`rarity-${rarity}`, { square, 'has-name': showName }]"
    @pointerenter="showTooltip" @pointermove="item && moveTooltip($event)" @pointerleave="hideTooltip">
    <button type="button" class="item-slot-button" :aria-label="label" @click="emit('edit')">
      <span v-if="item?.IconKey" class="item-icon" :class="{ layered: item.OverlayIconKey }">
        <img :src="iconUrl(item.IconKey)" alt="">
        <img v-if="item.OverlayIconKey" class="item-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
        <PalGearBadge :item="item" />
      </span>
      <span v-if="showName" class="slot-name">{{ label }}</span>
      <strong v-if="slot.count > 1" class="slot-count">{{ slot.count }}</strong>
      <span v-if="slot.warning" class="slot-warning">!</span>
      <span v-if="showDurability && slot.durability != null" class="durability">
        <i :style="{ width: `${Math.min(100, 100 * slot.durability / (maxDurability || 1))}%` }"></i>
      </span>
    </button>
    <button v-if="repairable" type="button" class="slot-repair"
      :title="palStore.getTranslatedText('Inventory_Repair')"
      :aria-label="palStore.getTranslatedText('Inventory_Repair')"
      @click.stop="emit('repair')"><UiIcon name="maximum" /></button>
    <button v-if="item && editable" type="button" class="slot-clear"
      :aria-label="palStore.getTranslatedText('Inventory_Clear')" @click.stop="emit('clear')">×</button>
  </div>

  <ItemHoverCard v-if="tooltipVisible && item" :item="item" :details-item="detailsItem" :count="slot.count"
    :client-x="tooltipPoint.clientX" :client-y="tooltipPoint.clientY" />
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
  z-index: 3;
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
.slot-repair {
  position: absolute; top: -.35rem; left: -.35rem;
  display: grid; place-items: center; width: 1.15rem; height: 1.15rem; padding: 0;
  border: 1px solid var(--editor-color-border); border-radius: 50%;
  background: var(--editor-color-control); color: var(--editor-color-text);
  cursor: pointer; line-height: 1;
}
.slot-repair:hover { background: var(--editor-color-control-hover); }
.slot-repair :deep(svg) { width: .7rem; height: .7rem; }
.rarity-1 .item-slot-button { background: linear-gradient(145deg, rgb(36 118 74 / .36), rgb(12 28 25 / .45)); }
.rarity-2 .item-slot-button { background: linear-gradient(145deg, rgb(33 101 166 / .4), rgb(13 27 47 / .48)); }
.rarity-3 .item-slot-button { background: linear-gradient(145deg, rgb(111 63 162 / .44), rgb(35 20 53 / .5)); }
.rarity-4 .item-slot-button { background: linear-gradient(145deg, rgb(158 104 24 / .5), rgb(52 35 14 / .52)); }
</style>
