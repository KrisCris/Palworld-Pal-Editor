<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import OverlayScrollArea from './OverlayScrollArea.vue'
import UiIcon from './UiIcon.vue'
import { filterSearchOptions } from './search-select'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
  searchPlaceholder: { type: String, default: '' },
  noResults: { type: String, default: '' },
  disabled: Boolean,
  ariaLabel: { type: String, default: '' },
  placement: { type: String, default: 'bottom' },
})
const emit = defineEmits(['update:modelValue'])
const disclosure = ref(null)
const popover = ref(null)
const open = ref(false)
const popoverStyle = ref({})
const query = ref('')
const tooltip = ref('')
let tooltipTimer
const selected = computed(() => props.options.find(option => option.value === props.modelValue))
const visibleOptions = computed(() => filterSearchOptions(props.options, query.value))

function choose(option) {
  if (option.disabled) return
  clearTooltip()
  emit('update:modelValue', option.value)
  query.value = ''
  disclosure.value.open = false
}

function close() {
  if (disclosure.value) disclosure.value.open = false
}

function updatePopoverPosition() {
  if (!open.value || !disclosure.value) return
  const trigger = disclosure.value.querySelector('summary')
  const rect = trigger?.getBoundingClientRect()
  if (!rect) return

  const viewportPadding = 12
  const gap = 4
  const width = Math.min(Math.max(rect.width, 416), window.innerWidth - viewportPadding * 2)
  const left = Math.min(
    Math.max(viewportPadding, rect.left),
    window.innerWidth - viewportPadding - width,
  )
  popoverStyle.value = props.placement === 'top'
    ? {
        left: `${left}px`,
        bottom: `${window.innerHeight - rect.top + gap}px`,
        width: `${width}px`,
      }
    : {
        left: `${left}px`,
        top: `${rect.bottom + gap}px`,
        width: `${width}px`,
      }
}

function onToggle() {
  open.value = Boolean(disclosure.value?.open)
  if (open.value) nextTick(updatePopoverPosition)
  else clearTooltip()
}

function queueTooltip(option) {
  clearTooltip()
  if (!option.tooltip) return
  tooltipTimer = setTimeout(() => { tooltip.value = option.tooltip }, 1200)
}

function clearTooltip() {
  clearTimeout(tooltipTimer)
  tooltip.value = ''
}

const closeOnOutsidePointer = event => {
  if (!open.value) return
  if (disclosure.value?.contains(event.target) || popover.value?.contains(event.target)) return
  close()
}
onMounted(() => {
  window.addEventListener('pointerdown', closeOnOutsidePointer)
  window.addEventListener('resize', updatePopoverPosition)
  window.addEventListener('scroll', updatePopoverPosition, true)
})
onBeforeUnmount(() => {
  clearTooltip()
  window.removeEventListener('pointerdown', closeOnOutsidePointer)
  window.removeEventListener('resize', updatePopoverPosition)
  window.removeEventListener('scroll', updatePopoverPosition, true)
})
</script>

<template>
  <details ref="disclosure" :class="['search-select', `search-select--${placement}`, { 'search-select--disabled': disabled }]"
    :aria-disabled="disabled" @click.capture="disabled && $event.preventDefault()" @toggle="onToggle">
    <summary :aria-label="ariaLabel">
      <span :class="['search-select__tone', selected?.tone && `search-select__tone--${selected.tone}`]" aria-hidden="true"></span>
      <img v-if="selected?.icon" :src="selected.icon" alt="">
      <span>{{ selected?.label || placeholder }}</span>
      <UiIcon name="more" />
    </summary>
  </details>
  <Teleport to="body">
    <div v-if="open" ref="popover" class="search-select__popover editor-glass-surface" :style="popoverStyle"
      @keydown.esc.stop="close">
      <label class="search-select__search">
        <UiIcon name="search" />
        <input type="search" v-model="query" :placeholder="searchPlaceholder" :aria-label="searchPlaceholder"
          @keydown.esc="close">
      </label>
      <OverlayScrollArea fit-content class="search-select__options-scroll">
        <div class="search-select__options overlay-scroll-area__viewport" role="listbox" :aria-label="ariaLabel">
          <button v-for="option in visibleOptions" :key="option.value" type="button" role="option"
            :aria-selected="option.value === modelValue" :disabled="option.disabled" @click="choose(option)"
            @pointerenter="queueTooltip(option)" @pointerleave="clearTooltip"
            @focus="queueTooltip(option)" @blur="clearTooltip">
            <span :class="['search-select__tone', option.tone && `search-select__tone--${option.tone}`]" aria-hidden="true"></span>
            <img v-if="option.icon" :src="option.icon" alt="">
            <span class="search-select__copy">
              <strong>{{ option.label }}</strong>
              <small v-if="option.description">{{ option.description }}</small>
            </span>
          </button>
          <p v-if="!visibleOptions.length" class="search-select__empty">{{ noResults }}</p>
        </div>
      </OverlayScrollArea>
      <p class="search-select__tooltip" :aria-hidden="!tooltip">
        <span v-if="tooltip" role="tooltip">{{ tooltip }}</span>
      </p>
    </div>
  </Teleport>
</template>

<style scoped>
.search-select {
  position: relative;
  min-width: 0;
  color: var(--editor-color-text);
}

.search-select summary {
  display: grid;
  min-height: 2.4rem;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-2);
  padding: 0 var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-control);
  cursor: pointer;
  list-style: none;
}

.search-select summary::-webkit-details-marker { display: none; }
.search-select summary > span:nth-last-child(2) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-select--disabled { opacity: .6; }
.search-select--disabled summary { cursor: not-allowed; }
.search-select img { width: 1.25rem; height: 1.25rem; object-fit: contain; }
.search-select__tone { display: none; width: .65rem; height: .65rem; border-radius: 50%; background: var(--editor-color-muted); }
.search-select__tone[class*='--'] { display: block; }
.search-select__tone--top { background: var(--editor-color-passive-top); }
.search-select__tone--high { background: var(--editor-color-passive-high); }
.search-select__tone--positive { background: var(--editor-color-passive-positive); }
.search-select__tone--negative { background: var(--editor-color-passive-negative); }

.search-select__popover {
  position: fixed;
  z-index: 1100;
  display: grid;
  box-sizing: border-box;
  gap: var(--editor-space-2);
  min-width: 0;
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  box-shadow: var(--editor-shadow-compact);
}

.search-select__search {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: var(--editor-space-2);
  min-height: 2.35rem;
  padding: 0 var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-control);
}

.search-select__search input {
  min-width: 0;
  border: 0;
  outline: 0;
  color: var(--editor-color-text);
  background: transparent;
}

.search-select__options {
  display: grid;
  max-height: min(24rem, 55vh);
  gap: var(--editor-space-1);
  overflow-y: auto;
}

.search-select__options-scroll {
  height: auto;
  max-height: min(24rem, 55vh);
}

.search-select__options button {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: center;
  gap: var(--editor-space-2);
  min-height: 2.75rem;
  padding: var(--editor-space-2);
  border: 1px solid transparent;
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  text-align: left;
  cursor: pointer;
}

.search-select__options button:hover,
.search-select__options button[aria-selected='true'] { border-color: var(--editor-color-focus); color: var(--editor-color-background); background: var(--editor-color-primary); }
.search-select__options button:hover .search-select__copy small,
.search-select__options button[aria-selected='true'] .search-select__copy small { color: var(--editor-color-background); }
.search-select__options button:disabled { border-color: var(--editor-color-disabled); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); cursor: not-allowed; }
.search-select__copy { display: grid; min-width: 0; }
.search-select__copy strong,
.search-select__copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-select__copy small { color: var(--editor-color-muted); font-size: .7rem; }
.search-select__empty { margin: 0; padding: var(--editor-space-3); color: var(--editor-color-muted); text-align: center; }
.search-select__tooltip {
  min-height: calc(1.45em + 2 * var(--editor-space-2) + 1px);
  max-height: 6rem;
  margin: 0;
  padding: var(--editor-space-2);
  overflow-y: auto;
  border-top: 1px solid var(--editor-color-border);
  color: var(--editor-color-text);
  font-size: .8rem;
  line-height: 1.45;
}

.search-select summary:focus-visible,
.search-select__search:focus-within,
.search-select__options button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

</style>
