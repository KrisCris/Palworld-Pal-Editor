<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const current = computed(() => palStore.CURRENT_MESSAGE)
const visibleText = computed(() => palStore.getMessageText(current.value))
const details = computed(() => [current.value?.code, current.value?.log]
  .filter(Boolean)
  .join('\n\n'))
const titleKeys = {
  success: 'Message_Title_Success',
  warning: 'Message_Title_Warning',
  error: 'Message_Title_Error',
}
const title = computed(() => palStore.getTranslatedText(
  titleKeys[current.value?.severity] || 'Message_Title_Warning',
))
const closeButton = ref()
let dismissTimer

const clearDismissTimer = () => {
  clearTimeout(dismissTimer)
  dismissTimer = undefined
}
const dismiss = () => {
  if (current.value) palStore.dismissMessage(current.value.id)
}

watch(current, async message => {
  clearDismissTimer()
  if (!message) return
  if (message.presentation === 'dialog') {
    await nextTick()
    closeButton.value?.focus()
    return
  }
  dismissTimer = setTimeout(
    () => palStore.dismissMessage(message.id),
    message.severity === 'success' ? 5000 : 8000,
  )
}, { immediate: true })

onBeforeUnmount(clearDismissTimer)
</script>

<template>
  <div v-if="current?.presentation === 'dialog'" class="message-layer">
    <section
      class="message-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="message-center-title"
      aria-describedby="message-center-description"
    >
      <h1 id="message-center-title">{{ title }}</h1>
      <p id="message-center-description">{{ visibleText }}</p>
      <label v-if="details" for="message-center-details">
        {{ palStore.getTranslatedText('Message_Details') }}
      </label>
      <textarea
        v-if="details"
        id="message-center-details"
        :value="details"
        readonly
        spellcheck="false"
        rows="12"
      />
      <button ref="closeButton" @click="dismiss">
        {{ palStore.getTranslatedText('Message_Close') }}
      </button>
    </section>
  </div>

  <aside
    v-else-if="current"
    :class="['message-toast', current.severity]"
    :role="current.severity === 'success' ? 'status' : 'alert'"
  >
    <div>
      <strong>{{ title }}</strong>
      <p>{{ visibleText }}</p>
    </div>
    <button
      :aria-label="palStore.getTranslatedText('Message_Close')"
      @click="dismiss"
    >
      ×
    </button>
  </aside>
</template>

<style scoped>
.message-layer {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(0, 0, 0, .62);
}

.message-dialog {
  width: min(42rem, calc(100vw - 2rem));
  padding: 1rem;
  border: 1px solid #b36b00;
  border-radius: .75rem;
  background: #3b2c18;
  box-shadow: 2px 2px 10px #262626;
}

.message-dialog h1,
.message-dialog p {
  margin: .4rem 0;
}

.message-dialog label {
  display: block;
  margin-top: .75rem;
}

.message-dialog textarea {
  box-sizing: border-box;
  width: 100%;
  margin-top: .25rem;
  padding: .75rem;
  resize: vertical;
  border: 1px solid #7e6847;
  border-radius: .4rem;
  color: #ffcf87;
  background: #181818;
  font-family: monospace;
}

.message-dialog button {
  min-height: 2.5rem;
  margin-top: .75rem;
  padding: .5rem 1rem;
  border: 0;
  border-radius: .5rem;
  color: whitesmoke;
  background: #3365da;
  cursor: pointer;
}

.message-toast {
  position: fixed;
  top: 3.5rem;
  right: 1rem;
  z-index: 2100;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  width: min(30rem, calc(100vw - 2rem));
  padding: .8rem 1rem;
  border: 1px solid #d39a32;
  border-radius: .6rem;
  color: whitesmoke;
  background: #3b2c18;
  box-shadow: 2px 2px 10px #111;
}

.message-toast.success {
  border-color: #2eaa67;
  background: #183b29;
}

.message-toast div {
  flex: 1;
}

.message-toast p {
  margin: .25rem 0 0;
}

.message-toast button {
  padding: 0;
  border: 0;
  color: whitesmoke;
  background: transparent;
  font-size: 1.4rem;
  cursor: pointer;
}
</style>
