<script setup>
import { computed, nextTick, ref, watch } from "vue";

import en from "../../i18n/en.js";
import fr from "../../i18n/fr.js";
import ja from "../../i18n/ja.js";
import zhCN from "../../i18n/zh-CN.js";
import {
  buildPalFamilies,
  hasVisibleVariant,
  moveListboxIndex,
  paldeckForRow,
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

const paldeck = row => paldeckForRow(row) || "—";
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
          <span v-if="displayRow?.Invalid" class="warning" aria-hidden="true">⚠️</span>
          <span v-if="displayRow?.Invalid" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
          {{ paldeck(displayRow) }} {{ displayRow?.I18n || pendingId || t('Editor_Pal_Selector_Select') }}
        </span>
        <small>{{ displayRow?.InternalName || props.modelValue }}</small>
      </span>
      <span aria-hidden="true">{{ open ? "▴" : "▾" }}</span>
    </button>

    <div v-if="open" class="selector-popover" role="dialog" :aria-label="t('Editor_Pal_Selector_Title')">
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
                  <span v-if="family.invalidOnly" class="warning" aria-hidden="true">⚠️</span>
                  <span v-if="family.invalidOnly" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
                  {{ family.Paldeck || "—" }} {{ family.Name }}
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
                  <span v-if="variant.warning" class="warning" aria-hidden="true">⚠️</span>
                  <span v-if="variant.warning" class="sr-only">{{ t("Editor_Pal_Selector_Warning") }}</span>
                  {{ paldeck(variant) }} {{ variant.I18n || variant.InternalName }}
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
  </div>
</template>

<style scoped>
.pal-species-selector {
  position: relative;
  width: min(42rem, 75vw);
}

button {
  color: rgb(208, 212, 226);
  border: 1px solid #686868;
  background: #272727;
  border-radius: .5rem;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  filter: grayscale(1);
}

.selector-trigger {
  display: grid;
  grid-template-columns: 2rem 1fr auto;
  align-items: center;
  gap: .5rem;
  width: 100%;
  min-height: 2.8rem;
  padding: .3rem .6rem;
  text-align: left;
  box-shadow: 2px 2px 10px rgb(38, 38, 38);
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
  color: #aeb2c0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.warning {
  color: #ffd27a;
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
  position: absolute;
  z-index: 20;
  top: calc(100% + .35rem);
  left: 0;
  display: flex;
  width: 100%;
  box-sizing: border-box;
  flex-direction: column;
  gap: .5rem;
  padding: .75rem;
  border: 1px solid #777;
  border-radius: .75rem;
  background: #202020;
  box-shadow: 0 .5rem 2rem #111;
}

.search-label {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.search-label input {
  box-sizing: border-box;
  width: 100%;
  padding: .55rem .7rem;
  border: 1px solid #686868;
  border-radius: .5rem;
  outline: none;
  color: whitesmoke;
  background: #303030;
}

.search-label input:focus,
button:focus-visible {
  outline: 2px solid #5b91ff;
  outline-offset: 1px;
}

.selector-panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .5rem;
}

.selector-pane {
  display: flex;
  height: 18rem;
  min-width: 0;
  box-sizing: border-box;
  flex-direction: column;
  align-items: stretch;
  gap: .25rem;
  overflow: hidden;
  padding: .35rem;
  border-radius: .5rem;
  background: #181818;
}

.selector-options {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  align-items: stretch;
  gap: .25rem;
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
  border-color: #5b91ff;
  background: #304d82;
}

.selector-actions {
  display: flex;
  justify-content: flex-end;
  gap: .5rem;
}

.selector-actions button {
  padding: .45rem .9rem;
}

.selector-actions .apply {
  border-color: #48a867;
  background: #267541;
}

@media (max-width: 760px) {
  .pal-species-selector {
    width: min(32rem, 70vw);
  }

  .selector-panes {
    grid-template-columns: 1fr;
  }

  .selector-pane {
    height: 10rem;
  }
}
</style>
