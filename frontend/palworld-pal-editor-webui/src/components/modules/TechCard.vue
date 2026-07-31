<script setup>
import { computed } from 'vue'

import UiIcon from './UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const props = defineProps({ item: { type: Object, required: true } })
const isLocked = computed(() => !palStore.SELECTED_PLAYER_DATA.UnlockedRecipeTechnologyNames.includes(props.item.InternalName))
const techName = computed(() => props.item.I18n.Name ?? props.item.InternalName)
const techState = computed(() => palStore.getTranslatedText(isLocked.value ? 'Editor_Tech_Locked' : 'Editor_Tech_Unlocked'))
const bgStyle = computed(() => ({
  backgroundImage: `url('/image/${props.item.InternalName.startsWith('SkillUnlock_') ? 'pals' : 'tech'}/${props.item.IconAccessKey}')`
}))
const toggleLock = () => palStore.SELECTED_PLAYER_DATA.toggleTech(props.item.InternalName, isLocked.value)
</script>

<template>
  <button type="button" :class="['tech', { 'tech--boss': item.BossTechnology, 'tech--locked': isLocked }]"
    :style="bgStyle" :aria-label="`${techName}: ${techState}`" :aria-pressed="!isLocked"
    :disabled="palStore.LOADING_FLAG" @click="toggleLock">
    <span class="tech-header">
      <UiIcon v-if="!item.I18n.Type" name="warning" />
      {{ item.I18n.Type ?? palStore.getTranslatedText('Editor_Tech_Invalid') }}
    </span>
    <span class="tech-state">{{ techState }}</span>
    <span class="tech-footer">{{ techName }}</span>
  </button>
</template>

<style scoped>
.tech {
  position: relative;
  width: 100%;
  min-width: 0;
  aspect-ratio: 4 / 5;
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

.tech--boss { border-color: var(--editor-color-ancient); background-color: color-mix(in srgb, var(--editor-color-ancient) 24%, var(--editor-color-control)); }
.tech--locked { filter: grayscale(.9); opacity: .62; }
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
.tech-header {
  top: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: .2rem;
}
.tech-state {
  top: 1.45rem;
  left: auto;
  right: .25rem;
  width: auto;
  border-radius: 999px;
  color: var(--editor-color-focus);
  background: color-mix(in srgb, var(--editor-color-background) 85%, transparent);
}
.tech-footer {
  bottom: 0;
  min-height: 2.6rem;
  display: grid;
  place-items: center;
  white-space: normal;
}
</style>
