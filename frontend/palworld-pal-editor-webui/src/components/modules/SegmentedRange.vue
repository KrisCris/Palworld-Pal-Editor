<script>
const clamp = (minimum, maximum, value) => Math.min(maximum, Math.max(minimum, value))

export function normalizeRangeSegments({ min = 0, max = 100, value = 0, segments = [] }) {
  const minimum = Number(min)
  const maximum = Math.max(minimum, Number(max))
  const span = maximum - minimum || 1
  const filled = clamp(0, span, Number(value) - minimum)
  const source = segments.length ? segments : [{ role: 'primary', value: filled }]
  const result = []
  let used = 0

  for (const segment of source) {
    const amount = clamp(0, filled - used, Number(segment.value) || 0)
    if (!amount) continue
    result.push({
      role: segment.role === 'item' ? 'item' : 'primary',
      start: used / span * 100,
      end: (used + amount) / span * 100,
    })
    used += amount
  }
  if (used < span) result.push({ role: 'empty', start: used / span * 100, end: 100 })
  return result
}
</script>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },
  name: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '' },
  segments: { type: Array, default: () => [] },
  thumbRole: { type: String, default: 'primary' },
})
const emit = defineEmits(['update:modelValue', 'change'])
const colors = {
  primary: 'var(--editor-slider-primary)',
  item: 'var(--editor-slider-item)',
  empty: 'var(--editor-slider-empty)',
}
const normalizedSegments = computed(() => normalizeRangeSegments({
  min: props.min,
  max: props.max,
  value: props.modelValue,
  segments: props.segments,
}))
const trackStyle = computed(() => ({
  '--segmented-range-track': `linear-gradient(to right, ${normalizedSegments.value.flatMap(segment => {
    const color = colors[segment.role]
    return [`${color} ${segment.start}%`, `${color} ${segment.end}%`]
  }).join(', ')})`,
  '--segmented-range-thumb': colors[props.thumbRole] || colors.primary,
}))
const numberValue = event => Number(event.target.value)
</script>

<template>
  <input
    class="segmented-range"
    type="range"
    :name="name"
    :min="min"
    :max="max"
    :step="step"
    :value="modelValue"
    :disabled="disabled"
    :aria-label="ariaLabel || name"
    :style="trackStyle"
    @input="emit('update:modelValue', numberValue($event))"
    @change="emit('change', numberValue($event))"
  >
</template>

<style scoped>
.segmented-range {
  width: 100%;
  height: 1.25rem;
  margin: 0;
  appearance: none;
  background: transparent;
  cursor: pointer;
}

.segmented-range::-webkit-slider-runnable-track {
  height: .45rem;
  border-radius: 999px;
  background: var(--segmented-range-track);
}

.segmented-range::-moz-range-track {
  height: .45rem;
  border: 0;
  border-radius: 999px;
  background: var(--segmented-range-track);
}

.segmented-range::-webkit-slider-thumb {
  width: 1rem;
  height: 1rem;
  margin-top: -.275rem;
  appearance: none;
  border: 2px solid var(--editor-color-text);
  border-radius: 50%;
  background: var(--segmented-range-thumb);
  box-shadow: var(--editor-shadow-compact);
}

.segmented-range::-moz-range-thumb {
  width: .8rem;
  height: .8rem;
  border: 2px solid var(--editor-color-text);
  border-radius: 50%;
  background: var(--segmented-range-thumb);
  box-shadow: var(--editor-shadow-compact);
}

.segmented-range:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 3px; }
.segmented-range:disabled { cursor: not-allowed; filter: grayscale(1); opacity: .55; }
</style>
