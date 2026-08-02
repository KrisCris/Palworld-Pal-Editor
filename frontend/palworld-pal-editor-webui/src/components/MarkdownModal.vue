<template>
    <div v-show="palStore.SHOW_DONATE_FLAG" class="modal-overlay" @click.self="close">
        <div class="modal-content">
            <button class="close-btn" @click="close">×</button>
            <div v-if="loading" class="modal-loading">Loading...</div>
            <div v-else-if="error" class="modal-error">{{ error }}</div>
            <div v-else class="modal-body markdown-content" v-html="markdownHtml"></div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from "vue";
import { marked } from "marked";
import { usePalEditorStore } from "@/stores/paleditor";

const palStore = usePalEditorStore();

const props = defineProps({
    url: {
        type: String,
        required: true,
    },
});

const markdownHtml = ref("");
const loading = ref(true);
const error = ref("");

const close = async () => {
    if (palStore.SAVE_LOADED_FLAG) {
        await palStore.shownDonate();
    }
    palStore.SHOW_DONATE_FLAG = false;
};

const fetchMarkdown = async () => {
    loading.value = true;
    error.value = "";
    try {
        const response = await fetch(props.url);
        if (!response.ok) throw new Error("Failed to fetch content");
        const markdownText = await response.text();
        markdownHtml.value = marked(markdownText); // Convert Markdown to HTML
    } catch (err) {
        error.value = "Failed to load content. Please try again later.";
        console.error("Error fetching markdown:", err);
    } finally {
        loading.value = false;
    }
};

const setLinksToOpenInNewWindow = () => {
    const markdownContainer = document.querySelector(".markdown-content");
    if (markdownContainer) {
        const links = markdownContainer.querySelectorAll("a");
        links.forEach(link => {
            link.setAttribute("target", "_blank");
            link.setAttribute("rel", "noopener noreferrer"); // For security
        });
    }
};

onMounted(() => {
    fetchMarkdown();
});

watch(markdownHtml, async () => {
    await nextTick()
    setLinksToOpenInNewWindow();
});
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: color-mix(in srgb, var(--editor-color-background) 82%, transparent);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background: var(--editor-color-surface-raised);
    color: var(--editor-color-text);
    position: relative;
    padding: 20px;
    border-radius: 8px;
    max-width: 80%;
    max-height: 80%;
    overflow-y: auto;
    box-shadow: var(--editor-shadow-compact);
    border: 1px solid var(--editor-color-border);
}

::v-deep(.markdown-content a) {
    all: unset;
    color: color-mix(in srgb, var(--editor-color-primary) 70%, var(--editor-color-text));
    font-weight: bold;
    cursor: pointer;
}

::v-deep(.markdown-content a:hover) {
    text-decoration: underline;
    color: var(--editor-color-focus);
}

.modal-loading,
.modal-error {
    text-align: center;
    margin-top: 20px;
    font-family: inherit;
    color: color-mix(in srgb, var(--editor-color-danger) 70%, var(--editor-color-text));
}

.close-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    color: var(--editor-color-text);
    font-size: 1.5rem;
    cursor: pointer;
}

.close-btn:hover {
    color: color-mix(in srgb, var(--editor-color-danger) 70%, var(--editor-color-text));
}

::v-deep(.markdown-content a:focus-visible),
.close-btn:focus-visible {
    outline: 2px solid var(--editor-color-focus);
    outline-offset: 2px;
}
</style>
