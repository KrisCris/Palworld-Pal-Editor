<script setup>
import { computed } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  size: { type: String, default: '2.5rem' },
  borderColor: { type: String, default: 'var(--editor-color-border)' },
  glowColor: { type: String, default: '' },
})

const style = computed(() => ({
  '--pal-portrait-size': props.size,
  '--pal-portrait-border': props.borderColor,
  ...(props.glowColor ? { '--pal-portrait-glow': props.glowColor } : {}),
}))
</script>

<template>
  <span :class="['pal-portrait', { 'has-glow': glowColor }]" :style="style">
    <img class="pal-portrait__image" :src="src" :alt="alt">
    <span class="pal-portrait__marker pal-portrait__marker--top-left" aria-hidden="true"><slot name="top-left" /></span>
    <span class="pal-portrait__marker pal-portrait__marker--top-right" aria-hidden="true"><slot name="top-right" /></span>
    <span class="pal-portrait__marker pal-portrait__marker--bottom-left" aria-hidden="true"><slot name="bottom-left" /></span>
    <span class="pal-portrait__marker pal-portrait__marker--bottom-right" aria-hidden="true"><slot name="bottom-right" /></span>
  </span>
</template>

<style scoped>
.pal-portrait {
  position: relative;
  display: inline-block;
  width: var(--pal-portrait-size);
  height: var(--pal-portrait-size);
  flex: 0 0 auto;
}

.pal-portrait__image {
  display: block;
  width: 100%;
  height: 100%;
  border: 2px solid var(--pal-portrait-border);
  border-radius: 50%;
  object-fit: contain;
  background: var(--editor-color-surface-subtle);
}

.has-glow .pal-portrait__image {
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--pal-portrait-glow) 45%, transparent),
    0 0 .9rem color-mix(in srgb, var(--pal-portrait-glow) 70%, transparent);
}

.pal-portrait__marker {
  position: absolute;
  width: clamp(.9rem, 36%, 2rem);
  height: clamp(.9rem, 36%, 2rem);
  transform: translate(-25%, -25%);
}

.pal-portrait__marker:empty { display: none; }
.pal-portrait__marker :deep(img) { display: block; width: 100%; height: 100%; object-fit: contain; }
.pal-portrait__marker :deep(.game-priority-icon) { filter: sepia(1) saturate(9) hue-rotate(355deg) brightness(1.12); }
.pal-portrait__marker :deep(.game-lucky-icon),
.pal-portrait__marker :deep(.game-dna-icon) { transform: scale(1.2); }
.pal-portrait__marker--top-left { top: 0; left: 0; }
.pal-portrait__marker--top-right { top: 0; right: 0; transform: translate(25%, -25%); }
.pal-portrait__marker--bottom-left {
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translate(-25%, 25%);
}
.pal-portrait__marker--bottom-left :deep(img) {
  width: 82%;
  height: 82%;
  flex: 0 0 82%;
}
.pal-portrait__marker--bottom-left :deep(img + img) { margin-left: -36%; }
.pal-portrait__marker--bottom-right { right: 0; bottom: 0; transform: translate(25%, 25%); }
</style>
