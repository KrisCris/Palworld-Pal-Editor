<script setup>
import NumberStepper from '@/components/modules/NumberStepper.vue'

const props = defineProps({
  modelValue: { type: Number, required: true },
  label: { type: String, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, required: true },
  step: { type: Number, default: 1 },
})
const emit = defineEmits(['update:modelValue'])

const clamp = value => {
  const number = Number(value)
  return Math.min(props.max, Math.max(props.min, Number.isFinite(number) ? number : props.min))
}
const setValue = value => emit('update:modelValue', clamp(value))
</script>

<template>
  <div class="number-slider-field">
    <span class="field-header">
      <span class="field-label">{{ label }}</span>
      <NumberStepper :model-value="modelValue" :label="label" :min="min" :max="max" :step="step"
        @update:model-value="setValue" />
    </span>
    <input class="number-range" type="range" :value="modelValue" :min="min" :max="max" :step="step"
      :aria-label="label" @input="setValue($event.target.value)">
  </div>
</template>

<style scoped>
.number-slider-field { display: grid; width: 100%; min-width: 0; gap: .55rem; color: var(--editor-color-muted); }
.field-header { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 1rem; }
.field-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.number-range { width: 100%; min-width: 0; margin: 0; accent-color: var(--editor-color-focus); cursor: pointer; }
</style>
