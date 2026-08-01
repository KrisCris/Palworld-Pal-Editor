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

import MarkdownModal from '@/components/MarkdownModal.vue'
import MessageCenter from '@/components/MessageCenter.vue'
import TopBar from '@/components/TopBar.vue'
import { usePalEditorStore } from '@/stores/paleditor'
import AuthView from '@/views/AuthView.vue'
import BackendErrorView from '@/views/BackendErrorView.vue'
import EditorView from '@/views/EditorView.vue'
import EntryView from '@/views/EntryView.vue'
import uiIconSprite from '@/assets/ui-icons.svg?raw'

const palStore = usePalEditorStore()
const runtimeError = computed(() => palStore.BACKEND_ERROR && palStore.APP_STATE !== 'backend-error')
const applicationDialog = computed(() => !palStore.BACKEND_ERROR && palStore.CURRENT_MESSAGE?.presentation === 'dialog')
const blockingOverlay = computed(() => runtimeError.value || applicationDialog.value)
const playersCollapsed = ref(readRosterCollapsed('editor.playersCollapsed'))
const palsCollapsed = ref(readRosterCollapsed('editor.palsCollapsed'))
const refreshPage = () => window.location.reload()
let previousFocus
const rememberFocus = event => {
  const control = event.target.closest?.('button, a[href], input, select, textarea, [tabindex]')
  if (control) previousFocus = control
}
watch(blockingOverlay, async (visible, wasVisible) => {
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
    :class="['app-content', { obscured: blockingOverlay }]"
    :inert="blockingOverlay || undefined"
    @focusin="rememberFocus"
  >
    <TopBar :players-collapsed="playersCollapsed" :pals-collapsed="palsCollapsed"
      @restore-players="playersCollapsed = false" @restore-pals="palsCollapsed = false" />

    <p v-if="palStore.APP_STATE === 'connecting'" role="status">
      {{ palStore.getTranslatedText('App_Connecting') }}
    </p>
    <BackendErrorView
      v-else-if="palStore.APP_STATE === 'backend-error'"
      startup
      :kind="palStore.BACKEND_ERROR?.kind"
      :message="palStore.BACKEND_ERROR?.message"
      :code="palStore.BACKEND_ERROR?.code"
      :log="palStore.BACKEND_ERROR?.log"
      :loading="palStore.LOADING_FLAG"
      @retry="refreshPage"
    />
    <AuthView v-else-if="palStore.APP_STATE === 'auth-required'" />
    <EntryView v-else-if="palStore.APP_STATE === 'entry'" />
    <EditorView v-else-if="palStore.APP_STATE === 'editor'"
      :players-collapsed="playersCollapsed" :pals-collapsed="palsCollapsed"
      @collapse-players="playersCollapsed = true" @collapse-pals="palsCollapsed = true" />

    <MarkdownModal
      v-if="palStore.APP_STATE === 'entry' || palStore.APP_STATE === 'editor'"
      url="/docs/keep_this_project_alive.md"
    />
  </div>

  <BackendErrorView
    v-if="runtimeError"
    :kind="palStore.BACKEND_ERROR.kind"
    :message="palStore.BACKEND_ERROR.message"
    :code="palStore.BACKEND_ERROR.code"
    :log="palStore.BACKEND_ERROR.log"
    :loading="palStore.LOADING_FLAG"
    @retry="refreshPage"
    @dismiss="palStore.clearBackendError"
  />
  <MessageCenter v-if="!palStore.BACKEND_ERROR" />
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
  filter: blur(4px);
  pointer-events: none;
  user-select: none;
}
</style>
