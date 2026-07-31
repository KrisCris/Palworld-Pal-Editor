<script setup>
import { computed, nextTick, ref, watch } from "vue";
import UiIcon from "./UiIcon.vue";

import en from "../../i18n/en.js";
import fr from "../../i18n/fr.js";
import ja from "../../i18n/ja.js";
import zhCN from "../../i18n/zh-CN.js";
import {
  buildPalFamilies,
  hasVisibleVariant,
  moveListboxIndex,
  palLabel,
} from "./pal-species-selector.js";

const props = defineProps({
  modelValue: { type: String, default: "" },
  rows: { type: [Object, Array], default: () => [] },
  hideInvalid: { type: Boolean, default: true },
  locale: { type: String, default: "en" },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "apply"]);

const translations = { en, fr, ja, "zh-CN": zhCN };
const t = key => translations[props.locale]?.[key] ?? en[key] ?? key;
const open = ref(false);
const query = ref("");
const selectedFamilyId = ref("");
const pendingId = ref(props.modelValue);
const triggerButton = ref(null);
const searchInput = ref(null);

const rowList = computed(() => Array.isArray(props.rows)
  ? props.rows
  : Object.values(props.rows ?? {}));
const families = computed(() => buildPalFamilies(
  rowList.value,
  props.modelValue,
  props.hideInvalid,
  query.value,
));
const savedRow = computed(() => rowList.value.find(
  row => row.InternalName === props.modelValue,
));
const pendingRow = computed(() => rowList.value.find(
  row => row.InternalName === pendingId.value,
));
const activeFamily = computed(() => (
  families.value.find(family => family.FamilyID === selectedFamilyId.value)
  ?? families.value.find(family => family.variants.some(
    variant => variant.InternalName === pendingId.value,
  ))
  ?? families.value.find(family => family.variants.some(
    variant => variant.InternalName === props.modelValue,
  ))
  ?? families.value[0]
));
const canApply = computed(() => (
  !props.disabled && hasVisibleVariant(activeFamily.value, pendingId.value)
));
const displayRow = computed(() => (
  open.value && canApply.value ? pendingRow.value : savedRow.value
));

watch(() => props.modelValue, value => { pendingId.value = value; });

function show() {
  pendingId.value = props.modelValue;
  open.value = true;
  query.value = "";
  selectedFamilyId.value = families.value.find(family => family.variants.some(
    variant => variant.InternalName === props.modelValue,
  ))?.FamilyID ?? "";
  nextTick(() => searchInput.value?.focus());
}

function close() {
  pendingId.value = props.modelValue;
  open.value = false;
  nextTick(() => triggerButton.value?.focus());
}

function selectVariant(id) {
  pendingId.value = id;
}

function apply() {
  if (!canApply.value) return;
  const id = pendingId.value;
  emit("update:modelValue", id);
  emit("apply", id);
  open.value = false;
  nextTick(() => triggerButton.value?.focus());
}

function navigateListbox(event) {
  if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
  const options = [...event.currentTarget.querySelectorAll("button[role=option]:not(:disabled)")];
  const nextIndex = moveListboxIndex(options.indexOf(document.activeElement), options.length, event.key);
  if (nextIndex < 0) return;
  event.preventDefault();
  options[nextIndex].focus();
  options[nextIndex].click();
}

const variantTabindex = (variant, index) => (
  hasVisibleVariant(activeFamily.value, pendingId.value)
    ? (variant.InternalName === pendingId.value ? 0 : -1)
    : (index ? -1 : 0)
);

</script>

<template>
  <div class="pal-species-selector" @keydown.esc.stop="close">
    <button
      ref="triggerButton"
      type="button"
      class="selector-trigger"
      data-testid="pal-species-trigger"
      :aria-expanded="open"
      aria-haspopup="dialog"
      @click="open ? close() : show()"
    >
      <img :src="`/image/pals/${displayRow?.IconKey || displayRow?.IconAccessKey || 'unknown'}`" alt="">
      <span class="trigger-copy">
        <span>
          <UiIcon v-if="displayRow?.Invalid" class="warning" name="warning" />
          <span v-if="displayRow?.Invalid" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
          {{ palLabel(displayRow, displayRow?.I18n || pendingId || t('Editor_Pal_Selector_Select')) }}
        </span>
        <small>{{ displayRow?.InternalName || props.modelValue }}</small>
      </span>
      <span aria-hidden="true">{{ open ? "▴" : "▾" }}</span>
    </button>

    <Teleport to="body">
    <div v-if="open" class="selector-popover" role="dialog" :aria-label="t('Editor_Pal_Selector_Title')"
      @keydown.esc.stop="close">
      <label class="search-label">
        <span>{{ t("Editor_Pal_Selector_Search") }}</span>
        <input
          ref="searchInput"
          v-model="query"
          type="search"
          data-testid="pal-species-search"
          :placeholder="t('Editor_Pal_Selector_Search_Placeholder')"
        >
      </label>

      <div class="selector-panes">
        <div class="selector-pane">
          <p class="pane-title">{{ t("Editor_Pal_Selector_Families") }}</p>
          <div
            class="selector-options"
            role="listbox"
            data-testid="pal-family-pane"
            :aria-label="t('Editor_Pal_Selector_Families')"
            @keydown="navigateListbox"
          >
            <button
              v-for="family in families"
              :key="family.FamilyID"
              type="button"
              role="option"
              data-testid="pal-family-option"
              :aria-selected="family.FamilyID === activeFamily?.FamilyID"
              :tabindex="family.FamilyID === activeFamily?.FamilyID ? 0 : -1"
              :class="{ selected: family.FamilyID === activeFamily?.FamilyID }"
              @click="selectedFamilyId = family.FamilyID"
            >
              <img :src="`/image/pals/${family.IconKey}`" alt="" loading="lazy">
              <span>
                <span>
                  <UiIcon v-if="family.invalidOnly" class="warning" name="warning" />
                  <span v-if="family.invalidOnly" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
                  {{ palLabel(family, family.Name) }}
                </span>
                <small>{{ family.FamilyID }}</small>
              </span>
            </button>
          </div>
          <p v-if="!families.length" class="empty">{{ t("Editor_Pal_Selector_No_Results") }}</p>
        </div>

        <div class="selector-pane">
          <p class="pane-title">{{ t("Editor_Pal_Selector_Variants") }}</p>
          <div
            class="selector-options"
            role="listbox"
            data-testid="pal-variant-pane"
            :aria-label="t('Editor_Pal_Selector_Variants')"
            @keydown="navigateListbox"
          >
            <button
              v-for="(variant, index) in activeFamily?.variants || []"
              :key="variant.InternalName"
              type="button"
              role="option"
              data-testid="pal-variant-option"
              :aria-selected="variant.InternalName === pendingId"
              :tabindex="variantTabindex(variant, index)"
              :class="{ selected: variant.InternalName === pendingId }"
              @click="selectVariant(variant.InternalName)"
            >
              <img :src="`/image/pals/${variant.IconKey || variant.IconAccessKey || 'unknown'}`" alt="" loading="lazy">
              <span>
                <span>
                  <UiIcon v-if="variant.warning" class="warning" name="warning" />
                  <span v-if="variant.warning" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
                  {{ palLabel(variant) }}
                </span>
                <small>{{ variant.InternalName }}</small>
              </span>
            </button>
          </div>
        </div>
      </div>

      <div class="selector-actions">
        <button type="button" @click="close">{{ t("Message_Close") }}</button>
        <button
          type="button"
          class="apply"
          data-testid="pal-species-apply"
          :disabled="!canApply"
          @click="apply"
        >{{ t("Editor_Pal_Selector_Apply") }}</button>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<style scoped>
.pal-species-selector {
  position: relative;
  width: 100%;
  min-width: 0;
  flex: 1 1 24rem;
}

button {
  color: var(--editor-color-text);
  border: 1px solid var(--editor-color-border);
  background: var(--editor-color-surface-raised);
  border-radius: var(--editor-radius-sm);
  cursor: pointer;
}

button:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
  cursor: not-allowed;
}

.selector-trigger {
  display: grid;
  grid-template-columns: 2rem 1fr auto;
  align-items: center;
  gap: .5rem;
  width: 100%;
  min-height: var(--editor-control-height);
  padding: var(--editor-space-1) var(--editor-space-3);
  text-align: left;
  background: var(--editor-color-control);
  box-shadow: var(--editor-shadow-compact);
}

img {
  width: 2rem;
  height: 2rem;
  object-fit: contain;
}

.trigger-copy,
.selector-pane button > span {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

small {
  overflow: hidden;
  color: var(--editor-color-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.warning {
  color: var(--editor-color-warning);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.selector-popover {
  position: fixed;
  z-index: 30;
  top: 50%;
  left: 50%;
  display: flex;
  width: min(52rem, calc(100vw - 2rem));
  max-height: calc(100vh - 2rem);
  box-sizing: border-box;
  flex-direction: column;
  gap: var(--editor-space-2);
  overflow-y: auto;
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-md);
  color: var(--editor-color-text);
  background: var(--editor-color-surface);
  box-shadow: var(--editor-shadow-compact);
  transform: translate(-50%, -50%);
}

.search-label {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.search-label input {
  box-sizing: border-box;
  width: 100%;
  min-height: var(--editor-control-height);
  padding: 0 var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  outline: none;
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.search-label input:focus,
button:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

.selector-panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--editor-space-2);
}

.selector-pane {
  display: flex;
  height: min(32rem, calc(100vh - 12rem));
  min-height: 18rem;
  min-width: 0;
  box-sizing: border-box;
  flex-direction: column;
  align-items: stretch;
  gap: var(--editor-space-1);
  overflow: hidden;
  padding: var(--editor-space-1);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: var(--editor-color-surface-subtle);
}

.selector-options {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  align-items: stretch;
  gap: var(--editor-space-1);
  overflow-y: auto;
}

.pane-title,
.empty {
  padding: .2rem .35rem;
}

.selector-pane button {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  align-items: center;
  gap: .45rem;
  padding: .4rem;
  text-align: left;
}

.selector-pane button:hover,
.selector-pane button.selected {
  border-color: var(--editor-color-focus);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.selector-pane button:hover small,
.selector-pane button.selected small {
  color: var(--editor-color-background);
}

.selector-pane button:hover .warning,
.selector-pane button.selected .warning {
  border-radius: 50%;
  color: var(--editor-color-warning);
  background: var(--editor-color-background);
}

.selector-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--editor-space-2);
}

.selector-actions button {
  min-height: var(--editor-control-height);
  padding: 0 var(--editor-space-4);
  border-color: var(--editor-color-border);
  background: var(--editor-color-surface-raised);
}

.selector-actions .apply {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.selector-actions .apply:disabled {
  border-color: var(--editor-color-disabled);
  color: var(--editor-color-muted);
  background: var(--editor-color-surface-subtle);
}

@media (max-width: 760px) {
  .pal-species-selector {
    width: 100%;
  }

  .selector-panes {
    grid-template-columns: 1fr;
  }

  .selector-pane {
    height: min(16rem, 30vh);
    min-height: 8rem;
  }
}
</style>
