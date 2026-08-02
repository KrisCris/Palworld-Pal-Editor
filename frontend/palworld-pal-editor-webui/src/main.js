import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'


import App from './App.vue'
import router from './router'
import { usePalEditorStore } from './stores/paleditor'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const palStore = usePalEditorStore(pinia)
app.config.errorHandler = (error, _instance, info) => {
    palStore.reportFrontendError(error, info)
}
window.addEventListener('error', event => {
    palStore.reportFrontendError(
        event.error || new Error(event.message),
        `${event.filename || 'browser'}:${event.lineno || 0}:${event.colno || 0}`,
    )
})
window.addEventListener('unhandledrejection', event => {
    palStore.reportFrontendError(event.reason, 'Unhandled promise rejection')
    event.preventDefault()
})

app.mount('#app')
