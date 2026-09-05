<script>
export const toggleTechnology = (store, item, isLocked) => store.toggleTech(item.InternalName, isLocked)
export const hasUnlockedTechnology = (names, internalName) => names.some(
  name => name.toLowerCase() === internalName.toLowerCase(),
)
</script>

<script setup>
import { computed } from 'vue'

import UiIcon from './modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'
import { usePlayersStore } from '@/stores/players'

const palStore = usePalEditorStore()
const playersStore = usePlayersStore()
const props = defineProps({ item: { type: Object, required: true } })
const isLocked = computed(() => !hasUnlockedTechnology(
  playersStore.selectedPlayer.UnlockedRecipeTechnologyNames,
  props.item.InternalName,
))
const techName = computed(() => props.item.I18n.Name ?? props.item.InternalName)
const techState = computed(() => palStore.getTranslatedText(isLocked.value ? 'Editor_Tech_Locked' : 'Editor_Tech_Unlocked'))
const bgStyle = computed(() => ({
  backgroundImage: `url('${palStore.backendAssetUrl(`/image/${props.item.InternalName.startsWith('SkillUnlock_') ? 'pals' : 'tech'}/${props.item.IconAccessKey}`)}')`
}))
const toggleLock = () => toggleTechnology(palStore, props.item, isLocked.value)
</script>

<template>
  <button type="button" :class="['tech', { 'tech--boss': item.BossTechnology, 'tech--locked': isLocked }]"
    :style="bgStyle" :aria-label="`${techName}: ${techState}`" :title="`${techName}: ${techState}`" :aria-pressed="!isLocked" @click="toggleLock">
    <span class="tech-header tech-type">
      <UiIcon v-if="!item.I18n.Type" name="warning" />
      {{ item.I18n.Type ?? palStore.getTranslatedText('Editor_Tech_Invalid') }}
    </span>
    <span class="tech-state tech-lock">{{ techState }}</span>
    <span class="tech-footer">{{ techName }}</span>
  </button>
</template>

<style scoped>
.tech {
  position: relative;
  inline-size: clamp(6.25rem, 8vw, 7.5rem);
  max-inline-size: 100%;
  aspect-ratio: 1;
  padding: 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--editor-color-primary) 70%, var(--editor-color-border));
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background-color: var(--editor-color-control);
  background-position: center;
  background-repeat: no-repeat;
  background-size: 68%;
  box-shadow: var(--editor-shadow-compact);
  cursor: pointer;
}

.tech:not(.tech--boss) { background-color: color-mix(in srgb, var(--editor-color-primary) 24%, var(--editor-color-control)); }
.tech--boss { border-color: var(--editor-color-ancient); background-color: color-mix(in srgb, var(--editor-color-ancient) 24%, var(--editor-color-control)); }
.tech--locked { filter: brightness(.58) saturate(.5); }
.tech:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 2px; }
.tech:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background-color: var(--editor-color-surface-subtle);
  filter: grayscale(1);
  cursor: not-allowed;
}
.tech-header,
.tech-footer,
.tech-state {
  position: absolute;
  left: 0;
  right: 0;
  padding: .2rem .35rem;
  overflow: hidden;
  background: color-mix(in srgb, var(--editor-color-background) 78%, transparent);
  font-size: .65rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tech-type {
  top: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: .2rem;
  min-height: 1.25rem;
}
.tech-lock {
  top: 1.45rem;
  left: auto;
  right: .2rem;
  width: max-content;
  max-width: calc(100% - .4rem);
  padding: .1rem .2rem;
  overflow: visible;
  border-radius: 999px;
  color: var(--editor-color-focus);
  background: color-mix(in srgb, var(--editor-color-background) 85%, transparent);
  overflow-wrap: anywhere;
  text-align: center;
  text-overflow: clip;
  white-space: normal;
}
.tech-footer {
  bottom: 0;
  min-height: 2.6rem;
  display: -webkit-box;
  align-content: center;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  white-space: normal;
}
</style>
