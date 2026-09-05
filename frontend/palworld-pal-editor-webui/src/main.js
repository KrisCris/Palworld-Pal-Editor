import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'


import App from './App.vue'
import router from './router'
import { useMessagesStore } from './stores/messages'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const messages = useMessagesStore(pinia)
app.config.errorHandler = (error, _instance, info) => {
    messages.reportFrontendError(error, info)
}
window.addEventListener('error', event => {
    messages.reportFrontendError(
        event.error || new Error(event.message),
        `${event.filename || 'browser'}:${event.lineno || 0}:${event.colno || 0}`,
    )
})
window.addEventListener('unhandledrejection', event => {
    messages.reportFrontendError(event.reason, 'Unhandled promise rejection')
    event.preventDefault()
})

app.mount('#app')
