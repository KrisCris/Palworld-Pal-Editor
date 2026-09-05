<script>
export function readRosterCollapsed(key) {
  try { return globalThis.localStorage.getItem(key) === 'true' }
  catch { return false }
}

export function persistRosterCollapsed(key, value) {
  try { globalThis.localStorage.setItem(key, String(value)) }
  catch { /* restricted storage keeps the in-memory state */ }
}
</script>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import MessageCenter from '@/components/MessageCenter.vue'
import SupportDialog from '@/components/SupportDialog.vue'
import TopBar from '@/components/TopBar.vue'
import { useBackendStore } from '@/stores/backend'
import { useMessagesStore } from '@/stores/messages'
import { usePalEditorStore } from '@/stores/paleditor'
import { useSessionStore } from '@/stores/session'
import AuthView from '@/views/AuthView.vue'
import BackendErrorView from '@/views/BackendErrorView.vue'
import EditorView from '@/views/EditorView.vue'
import EntryView from '@/views/EntryView.vue'
import uiIconSprite from '@/assets/ui-icons.svg?raw'

const backend = useBackendStore()
const messages = useMessagesStore()
const palStore = usePalEditorStore()
const sessionStore = useSessionStore()
const runtimeError = computed(() => backend.BACKEND_ERROR && sessionStore.appState !== 'backend-error')
const applicationDialog = computed(() => !backend.BACKEND_ERROR && messages.CURRENT_MESSAGE?.presentation === 'dialog')
const supportDialogVisible = computed(() =>
  palStore.SHOW_DONATE_FLAG && ['entry', 'editor'].includes(sessionStore.appState)
)
const blockingOverlay = computed(() => runtimeError.value || applicationDialog.value)
const modalOverlay = computed(() => blockingOverlay.value || supportDialogVisible.value)
// Spec 8.8: while an operation is running nothing in the app may start a second
// one or edit what the first is about to send. One region, one gate -- so a new
// control is covered by existing here rather than by remembering to disable itself.
const interactionBlocked = computed(() => modalOverlay.value || sessionStore.operationPending)
const playersCollapsed = ref(readRosterCollapsed('editor.playersCollapsed'))
const palsCollapsed = ref(readRosterCollapsed('editor.palsCollapsed'))
const refreshPage = () => window.location.reload()
let previousFocus
const rememberFocus = event => {
  const control = event.target.closest?.('button, a[href], input, select, textarea, [tabindex]')
  if (control) previousFocus = control
}
watch(modalOverlay, async (visible, wasVisible) => {
  if (!visible && wasVisible) {
    await nextTick()
    previousFocus?.focus()
    previousFocus = undefined
  }
}, { flush: 'sync' })
watch(playersCollapsed, value => persistRosterCollapsed('editor.playersCollapsed', value))
watch(palsCollapsed, value => persistRosterCollapsed('editor.palsCollapsed', value))
onMounted(palStore.bootstrap)
</script>

<template>
  <div class="ui-icon-sprite" aria-hidden="true" v-html="uiIconSprite"></div>
  <div
    :class="['app-content', { obscured: modalOverlay }]"
    :inert="interactionBlocked || undefined"
    @focusin="rememberFocus"
  >
    <TopBar :players-collapsed="playersCollapsed" :pals-collapsed="palsCollapsed"
      @restore-players="playersCollapsed = false" @restore-pals="palsCollapsed = false" />

    <p v-if="sessionStore.appState === 'connecting'" role="status">
      {{ palStore.getTranslatedText('App_Connecting') }}
    </p>
    <BackendErrorView
      v-else-if="sessionStore.appState === 'backend-error'"
      startup
      :kind="backend.BACKEND_ERROR?.kind"
      :message="backend.BACKEND_ERROR?.message"
      :code="backend.BACKEND_ERROR?.code"
      :log="backend.BACKEND_ERROR?.log"
      :loading="sessionStore.operationPending"
      @retry="refreshPage"
    />
    <AuthView v-else-if="sessionStore.appState === 'auth-required'" />
    <EntryView v-else-if="sessionStore.appState === 'entry'" />
    <EditorView v-else-if="sessionStore.appState === 'editor'"
      :players-collapsed="playersCollapsed" :pals-collapsed="palsCollapsed"
      @collapse-players="playersCollapsed = true" @collapse-pals="palsCollapsed = true" />

  </div>

  <SupportDialog v-if="sessionStore.appState === 'entry' || sessionStore.appState === 'editor'" />

  <BackendErrorView
    v-if="runtimeError"
    :kind="backend.BACKEND_ERROR.kind"
    :message="backend.BACKEND_ERROR.message"
    :code="backend.BACKEND_ERROR.code"
    :log="backend.BACKEND_ERROR.log"
    :loading="sessionStore.operationPending"
    @retry="refreshPage"
    @dismiss="backend.clearBackendError"
  />
  <MessageCenter v-if="!backend.BACKEND_ERROR" />
</template>

<style scoped>
.ui-icon-sprite {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}

.app-content {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
}

.app-content.obscured {
  pointer-events: none;
  user-select: none;
}
</style>
