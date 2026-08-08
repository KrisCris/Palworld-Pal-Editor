<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import UiIcon from '@/components/modules/UiIcon.vue'
import { usePalEditorStore } from '@/stores/paleditor'

const palStore = usePalEditorStore()
const closeButton = ref()
const openQrButton = ref()
const qrCloseButton = ref()
const selectedMethod = ref('kofi')
const expandedQr = ref()
const publicAsset = path => `${import.meta.env.BASE_URL}${path}`

const paymentMethods = [
  { id: 'kofi', label: 'Ko-fi', icon: 'coffee', href: 'https://ko-fi.com/connlost' },
  { id: 'paypal', label: 'PayPal', icon: 'card', href: 'https://www.paypal.com/paypalme/c0nnlost?country.x=US&locale.x=en_US' },
  { id: 'alipay', label: 'AliPay', icon: 'qr', qr: publicAsset('support/alipay.png') },
  { id: 'wechat', label: 'WeChat Pay', icon: 'qr', qr: publicAsset('support/wechat-pay.png') },
]

const selectedPayment = computed(() => paymentMethods.find(method => method.id === selectedMethod.value))
const expandedPayment = computed(() => paymentMethods.find(method => method.id === expandedQr.value))

const close = async () => {
  expandedQr.value = undefined
  palStore.SHOW_DONATE_FLAG = false
  if (palStore.SAVE_LOADED_FLAG) await palStore.shownDonate()
}

const openQr = async method => {
  expandedQr.value = method.id
  await nextTick()
  qrCloseButton.value?.focus()
}

const closeQr = async () => {
  expandedQr.value = undefined
  await nextTick()
  openQrButton.value?.focus()
}

watch(() => palStore.SHOW_DONATE_FLAG, async visible => {
  if (!visible) return
  selectedMethod.value = 'kofi'
  expandedQr.value = undefined
  await nextTick()
  closeButton.value?.focus()
})
</script>

<template>
  <div
    v-show="palStore.SHOW_DONATE_FLAG"
    class="support-overlay editor-modal-overlay"
    role="presentation"
    @click.self="close"
    @keydown.esc.stop="close"
  >
    <section
      class="support-dialog editor-glass-surface"
      role="dialog"
      aria-modal="true"
      aria-labelledby="support-dialog-title"
      aria-describedby="support-dialog-intro"
      :aria-hidden="expandedQr ? 'true' : undefined"
      :inert="expandedQr ? '' : undefined"
    >
      <header class="support-header">
        <img :src="publicAsset('icons/512.png')" alt="" class="support-logo">
        <div>
          <h2 id="support-dialog-title">{{ palStore.getTranslatedText('SupportDialog_Title') }}</h2>
          <p id="support-dialog-intro">{{ palStore.getTranslatedText('SupportDialog_Intro') }}</p>
        </div>
        <button
          ref="closeButton"
          type="button"
          class="support-close"
          :aria-label="palStore.getTranslatedText('Message_Close')"
          @click="close"
        >
          <UiIcon name="close" />
        </button>
      </header>

      <div class="support-content">
        <section class="support-panel support-financial">
          <div class="support-section-heading">
            <div>
              <h3>{{ palStore.getTranslatedText('SupportDialog_Financial_Title') }}</h3>
              <p>{{ palStore.getTranslatedText('SupportDialog_Financial_Description') }}</p>
            </div>
            <UiIcon name="heart" />
          </div>

          <div class="support-payment-grid">
            <button
              v-for="method in paymentMethods"
              :key="method.id"
              type="button"
              class="support-payment"
              :class="{ 'support-payment--selected': selectedMethod === method.id }"
              :aria-pressed="selectedMethod === method.id"
              aria-controls="support-payment-detail"
              @click="selectedMethod = method.id"
            >
              <UiIcon :name="method.icon" />
              <span>{{ method.label }}</span>
            </button>
          </div>

          <article id="support-payment-detail" class="support-payment-detail">
            <div class="support-payment-copy">
              <h4>{{ palStore.getTranslatedText('SupportDialog_Payment_Title', [selectedPayment.label]) }}</h4>
              <p>
                {{ palStore.getTranslatedText(
                  selectedPayment.href ? 'SupportDialog_Online_Description' : 'SupportDialog_QR_Description',
                  [selectedPayment.label],
                ) }}
              </p>
              <a
                v-if="selectedPayment.href"
                :href="selectedPayment.href"
                target="_blank"
                rel="noopener noreferrer"
                class="support-primary support-detail-action"
              >
                <UiIcon name="external-link" />
                {{ palStore.getTranslatedText('SupportDialog_Open_Payment', [selectedPayment.label]) }}
              </a>
              <button
                v-else
                ref="openQrButton"
                type="button"
                class="support-primary support-detail-action"
                @click="openQr(selectedPayment)"
              >
                <UiIcon name="external-link" />
                {{ palStore.getTranslatedText('SupportDialog_Open_QR') }}
              </button>
            </div>
            <div
              v-if="selectedPayment.qr"
              class="support-qr-crop support-qr-crop--compact"
              :class="`support-qr-crop--${selectedPayment.id}`"
            >
              <img
                :src="selectedPayment.qr"
                :alt="palStore.getTranslatedText('SupportDialog_QR_Alt', [selectedPayment.label])"
              >
            </div>
          </article>
        </section>

        <section class="support-panel">
          <div class="support-section-heading">
            <div>
              <h3>{{ palStore.getTranslatedText('SupportDialog_Other_Title') }}</h3>
              <!-- <p>{{ palStore.getTranslatedText('SupportDialog_Other_Description') }}</p> -->
            </div>
          </div>

          <nav class="support-action-list" :aria-label="palStore.getTranslatedText('SupportDialog_Other_Title')">
            <a href="https://discord.gg/FnuA95nMJ8" target="_blank" rel="noopener noreferrer">
              <UiIcon name="message" />
              <span>
                <strong>{{ palStore.getTranslatedText('Entry_Support_Community_Title') }}</strong>
                <small>{{ palStore.getTranslatedText('Entry_Support_Community_Description') }}</small>
              </span>
              <UiIcon name="external-link" />
            </a>
            <a href="https://github.com/KrisCris/Palworld-Pal-Editor" target="_blank" rel="noopener noreferrer">
              <UiIcon name="pull-request" />
              <span>
                <strong>{{ palStore.getTranslatedText('Entry_Support_Code_Title') }}</strong>
                <small>{{ palStore.getTranslatedText('Entry_Support_Code_Description') }}</small>
              </span>
              <UiIcon name="external-link" />
            </a>
            <a href="https://github.com/KrisCris/Palworld-Pal-Editor/issues" target="_blank" rel="noopener noreferrer">
              <UiIcon name="bug" />
              <span>
                <strong>{{ palStore.getTranslatedText('Entry_Support_Issue_Title') }}</strong>
                <small>{{ palStore.getTranslatedText('Entry_Support_Issue_Description') }}</small>
              </span>
              <UiIcon name="external-link" />
            </a>
          </nav>
        </section>
      </div>

      <footer class="support-footer">
        <p class="support-warning">
          <UiIcon name="warning" />
          <span>{{ palStore.getTranslatedText('Message_CN_AntiScam') }}</span>
        </p>
        <div class="support-footer-actions">
          <button type="button" class="support-secondary" @click="close">
            {{ palStore.getTranslatedText('SupportDialog_Not_Now') }}
          </button>
          <a
            href="https://github.com/KrisCris/Palworld-Pal-Editor"
            target="_blank"
            rel="noopener noreferrer"
            class="support-primary"
          >
            <UiIcon name="branch" />
            {{ palStore.getTranslatedText('SupportDialog_View_Project') }}
          </a>
        </div>
      </footer>
    </section>

    <div
      v-if="expandedPayment"
      class="support-qr-overlay editor-modal-overlay"
      role="presentation"
      @click.self="closeQr"
      @keydown.esc.stop="closeQr"
    >
      <section
        class="support-qr-dialog editor-glass-surface"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-qr-title"
      >
        <header>
          <h3 id="support-qr-title">
            {{ palStore.getTranslatedText('SupportDialog_QR_Title', [expandedPayment.label]) }}
          </h3>
          <button
            ref="qrCloseButton"
            type="button"
            class="support-close"
            :aria-label="palStore.getTranslatedText('Message_Close')"
            @click="closeQr"
          >
            <UiIcon name="close" />
          </button>
        </header>
        <div class="support-qr-crop support-qr-crop--large" :class="`support-qr-crop--${expandedPayment.id}`">
          <img
            :src="expandedPayment.qr"
            :alt="palStore.getTranslatedText('SupportDialog_QR_Alt', [expandedPayment.label])"
          >
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.support-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: clamp(var(--editor-space-3), 3vw, 2.5rem);
}

.support-dialog {
  width: min(72rem, 100%);
  max-height: min(52rem, calc(100dvh - 2rem));
  overflow: auto;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-lg);
  background: color-mix(in srgb, var(--editor-color-surface) 70%, transparent);
  box-shadow: var(--editor-glass-shadow), 0 2.2rem 5rem rgb(0 0 0 / 52%);
}

.support-header,
.support-footer,
.support-section-heading,
.support-payment,
.support-action-list a {
  display: flex;
  align-items: center;
}

.support-header {
  position: sticky;
  top: 0;
  z-index: 4;
  align-items: flex-start;
  gap: var(--editor-space-3);
  padding: var(--editor-space-5);
  border-bottom: 1px solid var(--editor-color-glass-border);
  background: var(--editor-color-glass-toolbar);
  -webkit-backdrop-filter: blur(18px) saturate(115%);
  backdrop-filter: blur(18px) saturate(115%);
}

.support-logo {
  width: 3rem;
  height: 3rem;
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
}

.support-header > div {
  min-width: 0;
  flex: 1;
}

.support-header h2,
.support-section-heading h3,
.support-header p,
.support-section-heading p,
.support-payment-detail h4,
.support-payment-detail p,
.support-warning {
  margin: 0;
}

.support-header h2 {
  font-size: clamp(1.35rem, 2vw, 1.8rem);
  line-height: 1.15;
}

.support-header p,
.support-section-heading p,
.support-action-list small,
.support-payment-detail p {
  color: var(--editor-color-muted);
}

.support-header p,
.support-section-heading p {
  margin-top: var(--editor-space-1);
}

.support-close,
.support-secondary,
.support-primary {
  min-height: 2.75rem;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
}

.support-close {
  display: grid;
  width: 2.75rem;
  place-items: center;
  flex: 0 0 auto;
}

.support-content {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(19rem, .8fr);
  gap: var(--editor-space-4);
  padding: var(--editor-space-4) var(--editor-space-5);
}

.support-panel {
  min-width: 0;
  padding: var(--editor-space-4);
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-surface-raised) 72%, transparent);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 7%), var(--editor-shadow-compact);
}

.support-financial {
  position: relative;
}

.support-section-heading {
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--editor-space-3);
  margin-bottom: var(--editor-space-4);
}

.support-section-heading > .ui-icon {
  color: var(--editor-color-danger);
}

.support-payment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--editor-space-2);
}

.support-payment {
  min-width: 0;
  min-height: 3.25rem;
  gap: var(--editor-space-2);
  padding: 0 var(--editor-space-3);
  font: inherit;
  color: var(--editor-color-text);
  text-decoration: none;
  cursor: pointer;
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  background: color-mix(in srgb, var(--editor-color-control) 86%, transparent);
}

.support-payment > span {
  min-width: 0;
  flex: 1;
}

.support-action-list a > .ui-icon:last-child {
  color: var(--editor-color-muted);
}

.support-payment:hover,
.support-payment:focus-visible {
  border-color: var(--editor-color-focus);
  background: var(--editor-color-control-hover);
}

.support-payment--selected {
  border-color: var(--editor-color-focus);
  color: var(--editor-color-focus);
  background: color-mix(in srgb, var(--editor-color-primary) 16%, var(--editor-color-surface));
  box-shadow: inset .2rem 0 0 var(--editor-color-focus);
}

.support-payment-detail {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--editor-space-4);
  min-height: 10rem;
  margin-top: var(--editor-space-3);
  padding: var(--editor-space-3);
  border-left: .2rem solid var(--editor-color-focus);
  border-radius: var(--editor-radius-md);
  background: color-mix(in srgb, var(--editor-color-control) 86%, transparent);
  box-shadow: var(--editor-shadow-compact);
}

.support-payment-detail h4 {
  font-size: 1.15rem;
}

.support-payment-detail p {
  margin-top: var(--editor-space-2);
}

.support-detail-action {
  width: fit-content;
  margin-top: var(--editor-space-3);
  padding-inline: var(--editor-space-3);
}

.support-qr-crop {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  flex: 0 0 auto;
  border: .5rem solid white;
  border-radius: var(--editor-radius-sm);
  background: white;
}

.support-qr-crop--compact {
  width: 8rem;
}

.support-qr-crop img {
  position: absolute;
  max-width: none;
}

.support-qr-crop--alipay img {
  top: -142%;
  left: -57%;
  width: 215%;
}

.support-qr-crop--wechat img {
  top: -72%;
  left: -50%;
  width: 200%;
}

.support-qr-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  padding: var(--editor-space-3);
}

.support-qr-dialog {
  width: min(32rem, 100%);
  padding: var(--editor-space-4);
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-lg);
  box-shadow: var(--editor-glass-shadow), 0 2rem 5rem rgb(0 0 0 / 60%);
}

.support-qr-dialog header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-3);
  margin-bottom: var(--editor-space-4);
}

.support-qr-dialog h3 {
  margin: 0;
}

.support-qr-crop--large {
  width: min(25rem, calc(100vw - 5rem));
  margin-inline: auto;
}

.support-action-list {
  display: grid;
  gap: var(--editor-space-2);
}

.support-action-list a {
  min-width: 0;
  min-height: 4.35rem;
  gap: var(--editor-space-3);
  padding: var(--editor-space-3);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: color-mix(in srgb, var(--editor-color-control) 86%, transparent);
  text-decoration: none;
}

.support-action-list a:hover,
.support-action-list a:focus-visible {
  border-color: var(--editor-color-focus);
  background: var(--editor-color-surface-raised);
}

.support-action-list a > .ui-icon:first-child {
  color: var(--editor-color-focus);
}

.support-action-list span {
  min-width: 0;
  flex: 1;
}

.support-action-list strong,
.support-action-list small {
  display: block;
}

.support-footer {
  position: sticky;
  bottom: 0;
  z-index: 3;
  justify-content: space-between;
  gap: var(--editor-space-4);
  padding: var(--editor-space-4) var(--editor-space-5);
  border-top: 1px solid var(--editor-color-glass-border);
  background: var(--editor-color-glass-toolbar);
  -webkit-backdrop-filter: blur(18px) saturate(115%);
  backdrop-filter: blur(18px) saturate(115%);
}

.support-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--editor-space-2);
  max-width: 48rem;
}

.support-warning .ui-icon {
  margin-top: .15em;
  flex: 0 0 auto;
  color: var(--editor-color-danger);
}

.support-footer-actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--editor-space-2);
}

.support-secondary,
.support-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--editor-space-2);
  padding: 0 var(--editor-space-4);
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

.support-primary {
  border-color: var(--editor-color-primary);
  color: var(--editor-color-background);
  background: var(--editor-color-primary);
}

.support-primary:hover,
.support-primary:focus-visible {
  background: var(--editor-color-primary-hover);
}

.support-close:hover,
.support-secondary:hover {
  border-color: var(--editor-color-focus);
  background: var(--editor-color-control-hover);
}

.support-close:focus-visible,
.support-secondary:focus-visible,
.support-primary:focus-visible,
.support-payment:focus-visible {
  outline: 2px solid var(--editor-color-focus);
  outline-offset: 2px;
}

@media (max-width: 52rem) {
  .support-content {
    grid-template-columns: 1fr;
  }

  .support-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .support-footer-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 34rem) {
  .support-overlay {
    padding: var(--editor-space-2);
  }

  .support-header,
  .support-content,
  .support-footer {
    padding: var(--editor-space-3);
  }

  .support-logo {
    display: none;
  }

  .support-payment-grid {
    grid-template-columns: 1fr;
  }

  .support-payment-detail {
    grid-template-columns: 1fr;
  }

  .support-qr-crop--compact {
    width: 7rem;
  }

  .support-footer-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
