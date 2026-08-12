<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  item: { type: Object, required: true },
  detailsItem: { type: Object, default: null },
  count: { type: Number, default: null },
  clientX: { type: Number, required: true },
  clientY: { type: Number, required: true },
})
const palStore = usePalEditorStore()
const cardRef = ref(null)
const position = ref({ left: '0px', top: '0px' })

const details = computed(() => props.detailsItem || props.item)
const rarity = computed(() => Math.max(0, Math.min(4, details.value?.Rarity ?? 0)))
const rarityName = computed(() => palStore.getTranslatedText(`Inventory_Rarity_${rarity.value}`))
const itemType = computed(() => palStore.getTranslatedText(`Inventory_Type_${props.item.TypeA}`))
const iconUrl = key => palStore.backendAssetUrl(`/image/items/${key}`)
const statOrder = ['PhysicalAttack', 'PhysicalDefense', 'HP', 'Shield', 'MagicAttack', 'MagicDefense', 'Weight', 'Price']
const effectLabels = new Set([
  'AirDash', 'AvoidDurationUp_EquipSkill', 'CaptureLevel', 'CollectItemDrop_NaturalObject', 'CraftSpeed',
  'CurveType', 'DamageUpIfEquipped_YakushimaMagicWeapon', 'DamageUpIfEquipped_YakushimaMeleeWeapon',
  'DamageUpIfEquipped_YakushimaRangedWeapon', 'DamageUpIfEquipped_YakushimaSummonWeapon', 'Defense',
  'Defuser_ExplosiveSpore', 'ExplosionResist', 'ForYakushimaDefenceRate', 'FriendshipPoint_Increase',
  'JumpCount_Increase', 'JumpPower_Increase', 'LifeSteal', 'MaxHP', 'MaxInventoryWeight', 'MoveSpeed',
  'PalExp_Increase', 'ShotAttack', 'TemperatureResist_Cold', 'TemperatureResist_Heat',
  'ElementBoost_Dark', 'ElementBoost_Dragon', 'ElementBoost_Earth', 'ElementBoost_Electricity',
  'ElementBoost_Fire', 'ElementBoost_Ice', 'ElementBoost_Leaf', 'ElementBoost_Normal', 'ElementBoost_Water',
  'ElementResist_Dark', 'ElementResist_Dragon', 'ElementResist_Earth', 'ElementResist_Electricity',
  'ElementResist_Fire', 'ElementResist_Ice', 'ElementResist_Leaf', 'ElementResist_Normal', 'ElementResist_Water',
])
const statValue = key => (key === 'Weight' || key === 'Price' ? props.item : details.value)?.Stats?.[key]
const statRows = computed(() => statOrder
  .filter(key => statValue(key))
  .map(key => ({ key, label: palStore.getTranslatedText(`Inventory_Stat_${key}`), value: statValue(key) })))
const humanize = value => value.replaceAll('_', ' ').replace(/([a-z])([A-Z])/g, '$1 $2')
const effectRows = computed(() => (details.value?.Effects || []).map(effect => ({
  ...effect,
  label: effectLabels.has(effect.EffectType)
    ? palStore.getTranslatedText(`Inventory_Effect_${effect.EffectType}`)
    : humanize(effect.EffectType),
})))
const signed = value => `${value > 0 ? '+' : ''}${Number(value).toLocaleString()}`

const placeCard = () => {
  const rect = cardRef.value?.getBoundingClientRect()
  const width = rect?.width || 320
  const height = rect?.height || 280
  let left = props.clientX + 14
  let top = props.clientY + 14
  if (left + width + 12 > window.innerWidth) left = props.clientX - width - 14
  if (top + height + 12 > window.innerHeight) top = props.clientY - height - 14
  position.value = {
    left: `${Math.max(12, left)}px`,
    top: `${Math.max(12, top)}px`,
  }
}

watch(() => [props.clientX, props.clientY, props.item, props.detailsItem, props.count], async () => {
  await nextTick()
  placeCard()
}, { immediate: true })
</script>

<template>
  <Teleport to="body">
    <aside ref="cardRef" class="item-hover-card" :class="`rarity-${rarity}`" :style="position" role="tooltip">
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
      <section class="tooltip-visual">
        <span class="tooltip-icon item-icon" :class="{ layered: item.OverlayIconKey }">
          <img :src="iconUrl(item.IconKey)" alt="">
          <img v-if="item.OverlayIconKey" class="item-icon-overlay" :src="iconUrl(item.OverlayIconKey)" alt="">
        </span>
        <span v-if="count != null" class="tooltip-count">
          <small>{{ palStore.getTranslatedText('Inventory_Count') }}</small>
          <strong>{{ count }}</strong>
        </span>
      </section>
      <dl v-if="statRows.length || effectRows.length" class="tooltip-properties">
        <template v-for="stat in statRows" :key="stat.key">
          <dt>{{ stat.label }}</dt>
          <dd>{{ Number(stat.value).toLocaleString() }}</dd>
        </template>
        <template v-for="(effect, index) in effectRows" :key="`${effect.PassiveSkillId}-${index}`">
          <dt>{{ effect.label }}</dt>
          <dd>{{ signed(effect.EffectValue) }}</dd>
        </template>
      </dl>
      <p>{{ item.Description }}</p>
    </aside>
  </Teleport>
</template>

<style scoped>
.item-hover-card {
  --rarity-accent: #9ca3af;
  --rarity-header: rgb(73 78 87 / .46);
  position: fixed;
  z-index: 2200;
  width: min(21rem, calc(100vw - 1.5rem));
  max-height: calc(100vh - 1.5rem);
  overflow: auto;
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
.tooltip-visual { position: relative; display: flex; min-height: 8.5rem; align-items: center; padding: .75rem 1.15rem; background: rgb(255 255 255 / .05); }
.item-icon { position: relative; display: grid; aspect-ratio: 1; place-items: center; }
.item-icon img { width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 4px 5px rgb(0 0 0 / .38)); }
.item-icon.layered > img:first-child { position: absolute; inset: 0; }
.item-icon .item-icon-overlay { position: absolute; inset: 10%; width: 80%; height: 80%; }
.item-hover-card .tooltip-icon { width: 7rem; }
.tooltip-count { position: absolute; right: .85rem; bottom: .7rem; display: flex; min-width: 7.5rem; align-items: center; justify-content: space-between; gap: 1rem; padding: .35rem .55rem; border: 1px solid var(--editor-color-border); background: rgb(7 16 23 / .68); }
.tooltip-count small { color: var(--editor-color-muted); }
.tooltip-properties { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .3rem .8rem; margin: 0; padding: .65rem .85rem; border-top: 1px solid var(--editor-color-border); background: rgb(0 0 0 / .12); font-size: .75rem; }
.tooltip-properties dt { min-width: 0; overflow: hidden; color: var(--editor-color-muted); text-overflow: ellipsis; white-space: nowrap; }
.tooltip-properties dd { margin: 0; color: var(--rarity-accent); font-weight: 700; text-align: right; }
.item-hover-card p { margin: 0; padding: .75rem .85rem; color: #d5e1ea; font-size: .83rem; line-height: 1.45; white-space: pre-line; }
</style>
