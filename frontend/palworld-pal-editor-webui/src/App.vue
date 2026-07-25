<script setup>
import { computed, nextTick, onMounted, watch } from 'vue'

import MarkdownModal from '@/components/MarkdownModal.vue'
import TopBar from '@/components/TopBar.vue'
import { usePalEditorStore } from '@/stores/paleditor'
import AuthView from '@/views/AuthView.vue'
import BackendErrorView from '@/views/BackendErrorView.vue'
import EditorView from '@/views/EditorView.vue'
import EntryView from '@/views/EntryView.vue'

const palStore = usePalEditorStore()
const runtimeError = computed(() => palStore.BACKEND_ERROR && palStore.APP_STATE !== 'backend-error')
const refreshPage = () => window.location.reload()
let previousFocus
const rememberFocus = event => {
  const control = event.target.closest?.('button, a[href], input, select, textarea, [tabindex]')
  if (control) previousFocus = control
}
watch(runtimeError, async (visible, wasVisible) => {
  if (!visible && wasVisible) {
    await nextTick()
    previousFocus?.focus()
    previousFocus = undefined
  }
}, { flush: 'sync' })
onMounted(palStore.bootstrap)
</script>

<template>
  <div
    :class="['app-content', { obscured: runtimeError }]"
    :inert="runtimeError || undefined"
    @focusin="rememberFocus"
  >
    <TopBar />

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
    <EditorView v-else-if="palStore.APP_STATE === 'editor'" />

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
</template>

<style scoped>
.app-content.obscured {
  filter: blur(4px);
  pointer-events: none;
  user-select: none;
}
</style>
