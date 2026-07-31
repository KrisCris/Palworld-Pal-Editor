<script setup>
import { computed, ref } from 'vue'

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
const query = ref('')
const selected = computed(() => props.options.find(option => option.value === props.modelValue))
const visibleOptions = computed(() => filterSearchOptions(props.options, query.value))

function choose(option) {
  if (option.disabled) return
  emit('update:modelValue', option.value)
  query.value = ''
  disclosure.value.open = false
}
</script>

<template>
  <details ref="disclosure" :class="['search-select', `search-select--${placement}`, { 'search-select--disabled': disabled }]"
    :aria-disabled="disabled" @click.capture="disabled && $event.preventDefault()">
    <summary :aria-label="ariaLabel">
      <span :class="['search-select__tone', selected?.tone && `search-select__tone--${selected.tone}`]" aria-hidden="true"></span>
      <img v-if="selected?.icon" :src="selected.icon" alt="">
      <span>{{ selected?.label || placeholder }}</span>
      <UiIcon name="more" />
    </summary>
    <div class="search-select__popover">
      <label class="search-select__search">
        <UiIcon name="search" />
        <input type="search" v-model="query" :placeholder="searchPlaceholder" :aria-label="searchPlaceholder"
          @keydown.esc="disclosure.open = false">
      </label>
      <div class="search-select__options" role="listbox" :aria-label="ariaLabel">
        <button v-for="option in visibleOptions" :key="option.value" type="button" role="option"
          :aria-selected="option.value === modelValue" :disabled="option.disabled" @click="choose(option)">
          <span :class="['search-select__tone', option.tone && `search-select__tone--${option.tone}`]" aria-hidden="true"></span>
          <img v-if="option.icon" :src="option.icon" alt="">
          <span class="search-select__copy">
            <strong>{{ option.label }}</strong>
            <small v-if="option.description">{{ option.description }}</small>
          </span>
        </button>
        <p v-if="!visibleOptions.length" class="search-select__empty">{{ noResults }}</p>
      </div>
    </div>
  </details>
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
  position: absolute;
  z-index: 40;
  top: calc(100% + var(--editor-space-1));
  left: 0;
  right: 0;
  display: grid;
  gap: var(--editor-space-2);
  min-width: min(26rem, 80vw);
  padding: var(--editor-space-2);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-raised);
  box-shadow: var(--editor-shadow-compact);
}

.search-select--top .search-select__popover {
  top: auto;
  bottom: calc(100% + var(--editor-space-1));
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

.search-select summary:focus-visible,
.search-select__search:focus-within,
.search-select__options button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@media (max-width: 480px) {
  .search-select__popover { position: fixed; inset: 15vh var(--editor-space-3) auto; min-width: 0; }
}
</style>
