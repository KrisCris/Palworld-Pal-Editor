<script setup>
import spriteUrl from '@/assets/ui-icons.svg'

defineProps({ name: { type: String, required: true } })
</script>

<template>
  <svg class="ui-icon" aria-hidden="true" focusable="false">
    <use :href="`${spriteUrl}#${name}`" />
  </svg>
</template>

<style scoped>
.ui-icon {
  width: 1em;
  height: 1em;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
  pointer-events: none;
}
</style>
