<script setup>
import { computed, onMounted, ref } from 'vue'
import { usePalEditorStore } from '@/stores/paleditor'

const props = defineProps({
  startup: Boolean,
  kind: String,
  message: String,
  code: String,
  log: String,
  loading: Boolean,
})
defineEmits(['retry', 'dismiss'])

const palStore = usePalEditorStore()
const connectionError = computed(() => props.kind === 'connection')
const descriptionKey = computed(() => connectionError.value
  ? props.startup ? 'BackendError_Startup' : 'BackendError_Connection_Runtime'
  : props.startup ? 'BackendError_Application_Startup' : 'BackendError_Runtime')
const details = computed(() => props.code || props.log
  ? [props.message, props.code, props.log].filter(Boolean).join('\n\n')
  : '')
const refreshButton = ref()
onMounted(() => refreshButton.value?.focus())
</script>

<template>
  <div :class="['error-layer', { startup, 'editor-modal-overlay': !startup }]">
    <section
      :class="['backend-error', { 'editor-glass-surface': !startup }]"
      :role="startup ? 'alert' : 'alertdialog'"
      :aria-modal="startup ? undefined : true"
      aria-labelledby="backend-error-title"
      aria-describedby="backend-error-description"
      aria-live="assertive"
    >
      <img v-if="startup" :alt="palStore.getTranslatedText('BackendError_Logo_Alt')" class="logo" src="@/assets/logo.ico" width="125" height="125" />
      <h1 id="backend-error-title">{{ palStore.getTranslatedText(connectionError ? 'BackendError_Connection_Title' : 'BackendError_Title') }}</h1>
      <p id="backend-error-description">{{ palStore.getTranslatedText(descriptionKey) }}</p>
      <code v-if="message && !details">{{ message }}</code>
      <label v-if="details" for="backend-error-details">
        {{ palStore.getTranslatedText('BackendError_Details') }}
      </label>
      <textarea
        v-if="details"
        id="backend-error-details"
        :value="details"
        readonly
        spellcheck="false"
        rows="12"
      />
      <div class="actions">
        <button ref="refreshButton" @click="$emit('retry')" :disabled="loading">
          {{ palStore.getTranslatedText('BackendError_Refresh') }}
        </button>
        <button v-if="!startup" class="secondary" @click="$emit('dismiss')" :disabled="loading">
          {{ palStore.getTranslatedText('BackendError_Dismiss') }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.error-layer {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.backend-error {
  width: min(42rem, calc(100vw - 2rem));
  padding: 1rem;
  border: 1px solid var(--editor-color-warning);
  border-radius: .75rem;
}
.error-layer.startup {
  top: 3rem;
  z-index: 10;
  background: var(--editor-color-surface);
}
.startup .backend-error {
  border: 0;
  background: transparent;
  box-shadow: none;
  text-align: center;
}
h1, p { margin: .4rem 0; }
code { margin: .75rem 0; color: var(--editor-color-warning); overflow-wrap: anywhere; }
label { display: block; margin-top: .75rem; }
textarea {
  box-sizing: border-box;
  width: 100%;
  margin-top: .25rem;
  padding: .75rem;
  resize: vertical;
  border: 1px solid var(--editor-color-border);
  border-radius: .4rem;
  color: var(--editor-color-warning);
  background: var(--editor-color-surface-subtle);
  font-family: monospace;
}
.actions { display: flex; gap: .75rem; margin-top: .75rem; }
.startup .actions { justify-content: center; }
button {
  min-height: 2.5rem;
  padding: .5rem 1rem;
  border: 0;
  border-radius: .5rem;
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
  cursor: pointer;
}
button.secondary { color: var(--editor-color-text); background: var(--editor-color-control-hover); }
button:disabled { color: var(--editor-color-muted); background: var(--editor-color-disabled); cursor: default; }
</style>
