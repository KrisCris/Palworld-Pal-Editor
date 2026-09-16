<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

import { moveRecentFocus } from './backend-server-selector-keys'
import UiIcon from '@/components/modules/UiIcon.vue'
import { normalizeBackendOrigin, readRecentBackends, writeStorage } from '@/services/backend-connection'
import { useAppStore } from '@/stores/app'
import { useAppShellStore } from '@/stores/app-shell'
import { useBackendStore } from '@/stores/backend'
import { useSessionStore } from '@/stores/session'

const appStore = useAppStore()
const shell = useAppShellStore()
const backend = useBackendStore()
const sessionStore = useSessionStore()
const open = ref(false)
const address = ref(backend.BACKEND_CANDIDATE)
const errorKey = ref('')
const trigger = ref(null)
const root = ref(null)
const popoverTop = ref('0px')
const pageOrigin = window.location.origin
const text = key => appStore.getTranslatedText(key)
const currentOrigin = computed(() => backend.BACKEND_ORIGIN || pageOrigin)
const candidateOrigin = computed(() => backend.BACKEND_CANDIDATE || pageOrigin)
const visibleRecent = computed(() => backend.BACKEND_RECENT.filter(origin => origin !== currentOrigin.value))
const triggerLabel = computed(() => `${text('BackendSelector_Label')}: ${candidateOrigin.value}, ${text(
  backend.BACKEND_CONNECTED ? 'BackendSelector_Connected' : 'BackendSelector_Disconnected')}`)
const busy = computed(() => sessionStore.operationPending)

const close = focus => {
  open.value = false
  errorKey.value = ''
  if (focus) trigger.value?.focus()
}
const positionPopover = () => {
  popoverTop.value = `${trigger.value?.getBoundingClientRect().bottom || 0}px`
}
const toggle = () => {
  open.value = !open.value
  errorKey.value = ''
  if (open.value) {
    address.value = backend.BACKEND_CANDIDATE
    positionPopover()
  }
}
const useBackend = async value => {
  if (busy.value) return
  errorKey.value = ''
  let origin
  try { origin = normalizeBackendOrigin(value, pageOrigin) }
  catch { errorKey.value = 'BackendSelector_Invalid_Address'; return }
  if (await shell.connectBackend(origin)) close(true)
  else errorKey.value = 'BackendSelector_Connection_Failed'
}
const removeRecent = origin => {
  backend.BACKEND_RECENT = backend.BACKEND_RECENT.filter(item => item !== origin)
  writeStorage(localStorage, 'PAL_BACKEND_RECENT', JSON.stringify(backend.BACKEND_RECENT))
}
const onPointerDown = event => {
  if (open.value && !root.value?.contains(event.target)) close(false)
}
const onKeyDown = event => {
  if (event.key === 'Escape' && open.value) close(true)
}
const onResize = () => {
  if (open.value) positionPopover()
}
const onRecentKeyDown = event => moveRecentFocus(event,
  [...event.currentTarget.closest('[role="menu"]').querySelectorAll('[role="menuitem"]:not(:disabled)')])

backend.BACKEND_RECENT = readRecentBackends(localStorage, pageOrigin)
window.addEventListener('pointerdown', onPointerDown)
window.addEventListener('keydown', onKeyDown)
window.addEventListener('resize', onResize)
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onPointerDown)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div ref="root" class="backend-selector">
    <button ref="trigger" class="backend-selector__trigger editor-button editor-button--icon" type="button" :disabled="busy" :aria-expanded="open"
      aria-controls="backend-server-popover" :aria-label="triggerLabel" @click="toggle">
      <UiIcon name="server" />
      <span class="backend-selector__status" :class="{ connected: backend.BACKEND_CONNECTED }"></span>
      <span class="backend-selector__state">{{ text(backend.BACKEND_CONNECTED ? 'BackendSelector_Connected' : 'BackendSelector_Disconnected') }}</span>
      <span class="backend-selector__chevron" aria-hidden="true"></span>
    </button>
    <section v-if="open" id="backend-server-popover" class="backend-selector__popover editor-glass-surface"
      :style="{ '--backend-selector-popover-top': popoverTop }" :aria-label="text('BackendSelector_Title')">
      <header class="backend-selector__header">
        <div>
          <h2>{{ text('BackendSelector_Title') }}</h2>
          <p>{{ text('BackendSelector_Description') }}</p>
        </div>
        <span class="backend-selector__connection" :class="{ connected: backend.BACKEND_CONNECTED }">
          <span class="backend-selector__status" :class="{ connected: backend.BACKEND_CONNECTED }"></span>
          {{ text(backend.BACKEND_CONNECTED ? 'BackendSelector_Connected' : 'BackendSelector_Disconnected') }}
        </span>
      </header>

      <div class="backend-selector__current">
        <span class="backend-selector__server-copy">
          <strong>{{ currentOrigin }}</strong>
          <small>
            {{ text('BackendSelector_Current') }}
            <template v-if="appStore.version"> · Pal Editor {{ appStore.version }}</template>
          </small>
        </span>
        <span class="backend-selector__current-label">{{ text('BackendSelector_Current') }}</span>
      </div>

      <div v-if="visibleRecent.length" class="backend-selector__recent">
        <strong>{{ text('BackendSelector_Recent') }}</strong>
        <ul role="menu" :aria-label="text('BackendSelector_Recent')">
          <li v-for="origin in visibleRecent" :key="origin" class="backend-selector__recent-row" role="none">
          <button class="backend-selector__recent-action" type="button" role="menuitem" :disabled="busy"
            @click="useBackend(origin)" @keydown="onRecentKeyDown">
            <span class="backend-selector__server-copy"><strong>{{ origin }}</strong></span>
          </button>
          <button class="backend-selector__recent-remove" type="button" role="menuitem"
            :aria-label="`${text('BackendSelector_Remove')}: ${origin}`" :disabled="busy" @click.stop="removeRecent(origin)" @keydown="onRecentKeyDown">
            <UiIcon name="close" />
          </button>
          </li>
        </ul>
      </div>

      <label class="backend-selector__address-label" for="backend-server-address">{{ text('BackendSelector_Other') }}</label>
      <div class="backend-selector__connect-row">
        <input id="backend-server-address" v-model="address" class="editor-control" type="text" autocomplete="url"
          :placeholder="text('BackendSelector_Address')" :disabled="busy" @keydown.enter.prevent="useBackend(address)">
        <button class="editor-button editor-button--primary" type="button" :disabled="busy" @click="useBackend(address)">
          {{ text('BackendSelector_Connect') }}
        </button>
      </div>
      <p v-if="errorKey" class="backend-selector__error" role="alert">{{ text(errorKey) }}</p>
      <button class="backend-selector__page-server" type="button" :disabled="busy" @click="useBackend('')">
        {{ text('BackendSelector_Use_Page_Server') }}
      </button>
      <p class="backend-selector__hint">{{ text('BackendSelector_Cors_Hint') }}</p>
    </section>
  </div>
</template>

<style scoped>
.backend-selector { position: relative; min-width: 0; }
.backend-selector__trigger { position: relative; gap: .35rem; }
.backend-selector__trigger:focus-visible, .backend-selector__recent-row button:focus-visible, .backend-selector__page-server:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 2px; }
.backend-selector__trigger:disabled, .backend-selector__popover button:disabled, .backend-selector__popover input:disabled { cursor: not-allowed; opacity: .65; }
.backend-selector__trigger .backend-selector__status { position: absolute; right: .28rem; bottom: .28rem; border: 2px solid var(--editor-color-surface-raised); }
.backend-selector__status { width: .55rem; height: .55rem; flex: 0 0 auto; border-radius: 50%; background: var(--editor-color-muted); }
.backend-selector__status.connected { background: var(--editor-color-success); }
.backend-selector__state { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.backend-selector__chevron { width: .42rem; height: .42rem; margin: 0 0 .22rem .05rem; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(45deg); }
.backend-selector__popover { position: absolute; z-index: 30; top: calc(100% + var(--editor-space-2)); right: 0; display: grid; width: min(44rem, calc(100vw - 2 * var(--editor-space-3))); box-sizing: border-box; gap: var(--editor-space-3); padding: var(--editor-space-4); border: 1px solid var(--editor-color-glass-border); border-radius: var(--editor-radius-md); }
.backend-selector__popover h2, .backend-selector__popover p { margin: 0; }
.backend-selector__popover h2 { font-size: 1.45rem; line-height: 1.2; }
.backend-selector__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--editor-space-4); }
.backend-selector__header > div { display: grid; gap: var(--editor-space-1); }
.backend-selector__header p, .backend-selector__server-copy small, .backend-selector__hint { color: var(--editor-color-muted); }
.backend-selector__connection { display: inline-flex; flex: 0 0 auto; align-items: center; gap: var(--editor-space-1); color: var(--editor-color-muted); }
.backend-selector__connection.connected { color: var(--editor-color-success); }
.backend-selector__current, .backend-selector__recent-row { display: flex; min-width: 0; align-items: center; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); background: var(--editor-color-control); }
.backend-selector__current { min-height: 4.5rem; justify-content: space-between; gap: var(--editor-space-3); padding: 0 var(--editor-space-3); border-color: var(--editor-color-primary); background: color-mix(in srgb, var(--editor-color-primary) 12%, var(--editor-color-control)); }
.backend-selector__server-copy { display: grid; min-width: 0; gap: .2rem; }
.backend-selector__server-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.backend-selector__current-label { flex: 0 0 auto; color: var(--editor-color-primary); }
.backend-selector__recent, .backend-selector__recent ul { display: grid; gap: var(--editor-space-2); margin: 0; padding: 0; }
.backend-selector__recent-row { display: flex; min-width: 0; align-items: center; gap: var(--editor-space-1); list-style: none; }
.backend-selector__recent-action { display: flex; flex: 1; min-width: 0; min-height: 3.75rem; align-items: center; padding: 0 var(--editor-space-3); border: 0; color: var(--editor-color-text); background: transparent; text-align: left; cursor: pointer; }
.backend-selector__recent-action:hover { background: var(--editor-color-control-hover); }
.backend-selector__recent-remove { display: grid; width: 2.25rem; min-height: 2.25rem; margin-right: var(--editor-space-2); place-items: center; border: 0; border-radius: var(--editor-radius-sm); color: var(--editor-color-muted); background: transparent; cursor: pointer; }
.backend-selector__recent-remove:hover { color: var(--editor-color-danger); background: var(--editor-color-surface-subtle); }
.backend-selector__address-label { margin-bottom: calc(-1 * var(--editor-space-2)); color: var(--editor-color-muted); }
.backend-selector__connect-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--editor-space-2); }
.backend-selector__connect-row .editor-button { min-width: 7rem; }
.backend-selector__error { padding: var(--editor-space-2) var(--editor-space-3); border: 1px solid var(--editor-color-danger); border-radius: var(--editor-radius-sm); color: var(--editor-color-danger); background: color-mix(in srgb, var(--editor-color-danger) 10%, var(--editor-color-control)); }
.backend-selector__page-server { justify-self: start; padding: 0; border: 0; color: var(--editor-color-primary); background: transparent; cursor: pointer; }
.backend-selector__page-server:hover { color: var(--editor-color-primary-hover); text-decoration: underline; }
.backend-selector__hint { padding-top: var(--editor-space-3); border-top: 1px solid var(--editor-color-border); }
@media (max-width: 760px) {
  .backend-selector__popover {
    position: fixed;
    top: calc(var(--backend-selector-popover-top) + var(--editor-space-1));
    right: var(--editor-space-3);
    width: min(44rem, calc(100vw - 2 * var(--editor-space-3)));
    max-height: calc(100vh - var(--backend-selector-popover-top) - var(--editor-space-2));
    overflow: auto;
  }
}
@media (max-width: 520px) {
  .backend-selector__popover { padding: var(--editor-space-3); }
  .backend-selector__header { display: grid; }
  .backend-selector__connect-row { grid-template-columns: 1fr; }
  .backend-selector__connect-row .editor-button { width: 100%; }
}
</style>
