<script setup>
import { computed } from 'vue'

import { useCatalogsStore } from '@/stores/catalogs'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  item: { type: Object, required: true },
})
const catalogsStore = useCatalogsStore()
const palStore = usePalEditorStore()
const pal = computed(() => catalogsStore.palsByName[props.item.PalGearCharacterId])
const iconKey = computed(() => pal.value?.IconKey || pal.value?.IconAccessKey)
const name = computed(() => pal.value?.I18n || props.item.PalGearCharacterId)
</script>

<template>
  <span v-if="iconKey" class="pal-gear-badge" :title="name" aria-hidden="true">
    <img :src="palStore.backendAssetUrl(`/image/pals/${iconKey}`)" alt="">
  </span>
</template>

<style scoped>
.pal-gear-badge {
  position: absolute;
  z-index: 2;
  top: 0;
  left: 0;
  display: grid;
  width: clamp(1.1rem, 33%, 1.55rem);
  aspect-ratio: 1;
  place-items: center;
  pointer-events: none;
}

.pal-gear-badge img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 2px 3px rgb(0 0 0 / .72));
}
</style>
