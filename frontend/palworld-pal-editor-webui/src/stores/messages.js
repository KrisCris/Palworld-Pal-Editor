// Everything the user is told, in one queue.
//
// Toasts, dialogs and confirmations are one list rather than three, because they
// compete for the same screen and the ordering between them matters: a dialog
// asks something and jumps ahead of the toasts, which are only reporting. One
// queue is the only place that ordering can be decided once.
//
// This store is the bottom of the store graph -- it imports only the app store,
// for the locale. Every other store may report through it, which is the whole
// reason it is not part of the app shell: a store that reports a failed request
// should not have to import the shell that imports it.
//
// It has no opinion about what a failure means. Deciding that an expired token
// means asking for the password again, or that nothing answered means the
// backend is gone, is `stores/backend`.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { translate } from "../i18n/index.js";
import { useAppStore } from "./app.js";

export const useMessagesStore = defineStore("messages", () => {
    const app = useAppStore();

    const MESSAGE_QUEUE = ref([]);
    const CURRENT_MESSAGE = computed(() => MESSAGE_QUEUE.value[0] ?? null);
    let nextMessageId = 1;

    function getTranslatedText(translationKey, args = []) {
        return translate(app.locale, translationKey, args);
    }

    // A dialog goes ahead of any toast already waiting: the toasts are reporting
    // something that already happened, and the dialog is asking about something
    // that has not.
    function showMessage(message) {
        const entry = { id: nextMessageId++, args: [], ...message };
        if (entry.presentation == "dialog") {
            const firstToast = MESSAGE_QUEUE.value.findIndex(
                item => item.presentation == "toast"
            );
            MESSAGE_QUEUE.value.splice(
                firstToast < 0 ? MESSAGE_QUEUE.value.length : firstToast,
                0,
                entry
            );
        } else {
            MESSAGE_QUEUE.value.push(entry);
        }
        return entry.id;
    }

    function showToast(messageKey, severity = "warning", args = []) {
        return showMessage({ severity, presentation: "toast", messageKey, args });
    }

    // Resolves when the user answers, so a caller can `await` the question
    // instead of splitting itself in two around a callback.
    function confirmMessage(messageKey, args = []) {
        return new Promise(resolve => {
            showMessage({
                severity: "warning",
                presentation: "dialog",
                messageKey,
                args,
                confirmation: true,
                resolve,
            });
        });
    }

    // Closing a question without answering it is an answer: no.
    function dismissMessage(id) {
        const index = MESSAGE_QUEUE.value.findIndex(message => message.id == id);
        if (index < 0) return;
        const [message] = MESSAGE_QUEUE.value.splice(index, 1);
        if (message.confirmation) message.resolve(false);
    }

    function respondToMessage(id, confirmed) {
        const index = MESSAGE_QUEUE.value.findIndex(message => message.id == id);
        if (index < 0) return;
        const [message] = MESSAGE_QUEUE.value.splice(index, 1);
        if (message.confirmation) message.resolve(confirmed);
    }

    // A message carries keys rather than sentences, so it is rendered in whatever
    // language is current when it is shown rather than when it was queued. An
    // argument can be a key too -- that is how "Failed to {{0}}" names the
    // operation in the user's own language.
    function getMessageText(message) {
        if (message?.message) return message.message;
        const args = (message?.args || []).map(arg =>
            arg?.translationKey ? getTranslatedText(arg.translationKey) : arg
        );
        return getTranslatedText(message?.messageKey, args);
    }

    // A backend that answered with a failure, from the `{status, data, msg}`
    // endpoints that predate the REST envelope.
    function reportOperationError(operationKey, response) {
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Operation_Failed",
            args: [{ translationKey: operationKey }],
            code: response?.data?.error?.code || operationKey,
            log: response?.data?.error?.log || response?.msg,
        });
    }

    // Our own bug. Reported with the stack, because nobody can act on a message
    // that does not say where the fault is, and logged as well so it survives the
    // user dismissing the dialog.
    function reportFrontendError(error, context = "Frontend") {
        const exception = error instanceof Error ? error : new Error(String(error));
        console.error(context, exception);
        return showMessage({
            severity: "error",
            presentation: "dialog",
            messageKey: "Message_Unexpected_Frontend_Error",
            args: [context],
            code: exception.name,
            log: exception.stack || exception.message,
        });
    }

    return {
        MESSAGE_QUEUE,
        CURRENT_MESSAGE,

        getTranslatedText,
        getMessageText,
        showMessage,
        showToast,
        confirmMessage,
        dismissMessage,
        respondToMessage,
        reportOperationError,
        reportFrontendError,
    };
});
