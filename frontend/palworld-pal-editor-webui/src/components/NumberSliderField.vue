<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Number, required: true },
  label: { type: String, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, required: true },
  step: { type: Number, default: 1 },
})
const emit = defineEmits(['update:modelValue'])
const draft = ref('')

const clamp = value => {
  const number = Number(value)
  return Math.min(props.max, Math.max(props.min, Number.isFinite(number) ? number : props.min))
}
const setValue = value => emit('update:modelValue', clamp(value))
const adjust = direction => setValue(props.modelValue + direction * props.step)
const edit = event => {
  draft.value = event.target.value
  const value = Number(draft.value)
  if (draft.value !== '' && Number.isFinite(value) && value >= props.min && value <= props.max) setValue(value)
}
const commit = () => {
  const value = clamp(draft.value)
  draft.value = String(value)
  setValue(value)
}

watch(() => props.modelValue, value => { draft.value = String(clamp(value)) }, { immediate: true })
</script>

<template>
  <div class="number-slider-field">
    <span class="field-header">
      <span class="field-label">{{ label }}</span>
      <span class="number-stepper">
        <input class="number-input" type="number" :value="draft" :min="min" :max="max" :step="step"
          @input="edit" @blur="commit" @keydown.enter.prevent="commit">
        <button type="button" class="stepper-button stepper-up" :disabled="modelValue >= max"
          :aria-label="`${label} +${step}`" @click="adjust(1)">▴</button>
        <button type="button" class="stepper-button stepper-down" :disabled="modelValue <= min"
          :aria-label="`${label} -${step}`" @click="adjust(-1)">▾</button>
      </span>
    </span>
    <input class="number-range" type="range" :value="modelValue" :min="min" :max="max" :step="step"
      :aria-label="label" @input="setValue($event.target.value)">
  </div>
</template>

<style scoped>
.number-slider-field { display: grid; width: 100%; min-width: 0; gap: .55rem; color: var(--editor-color-muted); }
.field-header { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 1rem; }
.field-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.number-stepper {
  display: grid;
  width: 7rem;
  height: 2.2rem;
  flex: 0 0 auto;
  grid-template: 1fr 1fr / minmax(0, 1fr) 1.55rem;
  overflow: hidden;
  border: 1px solid var(--editor-color-border);
  border-radius: .65rem;
  background: rgb(0 0 0 / .24);
  transition: border-color .15s ease, box-shadow .15s ease;
}
.number-stepper:focus-within { border-color: var(--editor-color-focus); box-shadow: 0 0 0 2px color-mix(in srgb, var(--editor-color-focus) 24%, transparent); }
.number-input {
  grid-row: 1 / 3;
  min-width: 0;
  padding: .35rem .55rem;
  border: 0;
  outline: 0;
  color: var(--editor-color-text);
  background: transparent;
  font: inherit;
  font-variant-numeric: tabular-nums;
  text-align: right;
  appearance: textfield;
}
.number-input::-webkit-inner-spin-button, .number-input::-webkit-outer-spin-button { margin: 0; appearance: none; }
.stepper-button {
  display: grid;
  padding: 0;
  border: 0;
  border-left: 1px solid var(--editor-color-border);
  color: var(--editor-color-muted);
  background: rgb(255 255 255 / .045);
  line-height: 1;
  cursor: pointer;
  place-items: center;
}
.stepper-up { border-bottom: 1px solid var(--editor-color-border); }
.stepper-button:hover:not(:disabled) { color: var(--editor-color-text); background: rgb(255 255 255 / .11); }
.stepper-button:disabled { opacity: .35; cursor: not-allowed; }
.number-range { width: 100%; min-width: 0; margin: 0; accent-color: var(--editor-color-focus); cursor: pointer; }
</style>
