<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import OverlayScrollArea from "@/components/modules/OverlayScrollArea.vue";
import PalBriefPanel from "@/components/modules/PalBriefPanel.vue";
import {
  buildStorageMoveGroups,
  moveReasonKey,
} from "@/components/modules/pal-storage-move";
import { formatStorageLabel } from "@/components/modules/pal-storage-label";
import { usePalEditorStore } from "@/stores/paleditor";
import { usePalsStore } from "@/stores/pals";
import { playerRosterKey, useRostersStore } from "@/stores/rosters";
import { useStoragesStore } from "@/stores/storages";

const emit = defineEmits(["close"]);
const palStore = usePalEditorStore();
const palsStore = usePalsStore();
const rostersStore = useRostersStore();
const storagesStore = useStoragesStore();
const pal = computed(() => palsStore.selectedPal);
const dialog = ref(null);
const updateAction = ref(null);
const preview = ref(null);
const previewScale = ref(1);
const activeGroupKey = ref("");
const pendingStorageKey = ref("");
const conflict = computed(() => storagesStore.conflict);
let previewFrame = 0;

const groups = computed(() => buildStorageMoveGroups(
  storagesStore.storages,
  rostersStore.activePlayerUid
    ? playerRosterKey(rostersStore.activePlayerUid)
    : null,
));
const activeGroup = computed(() => (
  groups.value.find(group => group.key === activeGroupKey.value) ?? groups.value[0]
));
// A group whose label is null is one of the fixed groups, whose heading is a
// phrase this app has translated rather than a name the save holds.
const FIXED_GROUP_KEYS = {
  bases: "Editor_Move_Group_Bases",
  "global-palbox": "Editor_Container_GlobalPalbox",
};
const groupLabel = group => group.label || palStore.getTranslatedText(
  FIXED_GROUP_KEYS[group.key] ?? "Editor_Move_Group_Other",
);
const storageLabel = storage => formatStorageLabel(
  storage,
  palStore.getTranslatedText,
);
// Until the answer for a row is in, the row is not offered: an unanswered target
// is not a permitted one.
const capabilityOf = storage => storagesStore.capability(storage.storageKey);
const disabledReasonKey = storage => moveReasonKey(capabilityOf(storage)?.reason);
const isOffered = storage => Boolean(capabilityOf(storage)?.allowed);
const pendingCapability = computed(() => storagesStore.capability(pendingStorageKey.value));
// The Pal an overwrite would land on, and where it is sitting. `label` is what the
// backend called that place; the directory has the translated name when it holds it.
const conflictTargetLabel = computed(() => {
  const target = storagesStore.conflictTarget;
  if (!target) return "";
  return storagesStore.storage(target.storageKey)
    ? storageLabel(storagesStore.storage(target.storageKey))
    : target.label || "";
});
// A move is a move; a copy into or out of the Global Palbox leaves the source
// where it is. Which one this is comes from the backend's `effect`.
const isGlobalTransfer = computed(() => Boolean(
  pendingCapability.value?.effect && pendingCapability.value.effect !== "relocate",
));
const previewStyle = computed(() => ({
  "--move-preview-scale": previewScale.value,
}));

function updatePreviewScale() {
  previewFrame = 0;
  if (!preview.value || !updateAction.value) return;

  const previewTop = preview.value.getBoundingClientRect().top;
  const actionTop = updateAction.value.getBoundingClientRect().top;
  const availableHeight = Math.max(0, actionTop - previewTop - 12);
  const naturalHeight = preview.value.scrollHeight;
  previewScale.value = naturalHeight > 0
    ? Math.min(1, availableHeight / naturalHeight)
    : 1;
}

function schedulePreviewScale() {
  if (previewFrame) cancelAnimationFrame(previewFrame);
  previewFrame = requestAnimationFrame(updatePreviewScale);
}

function selectStorage(storage) {
  if (!isOffered(storage)) return;
  pendingStorageKey.value = storage.storageKey;
}

async function movePal() {
  if (!pendingStorageKey.value) return;
  if (await palStore.movePal(pendingStorageKey.value)) closeDialog();
}

async function updatePal() {
  if (await palStore.updateConflictingPal()) closeDialog();
}

async function jumpToPal() {
  if (await palStore.jumpToConflictingPal()) closeDialog(false);
}

function closeDialog(clearConflict = true) {
  if (clearConflict) storagesStore.clearConflict();
  emit("close");
}

onMounted(async () => {
  storagesStore.clearConflict();
  storagesStore.clearCapabilities();
  // Open on the group the Pal is already in, unless it is the only place in that
  // group -- a Pal alone in the Global Palbox would otherwise open on a list of
  // one row it cannot use. Then the list the user came from is the better start.
  const sourceGroup = groups.value.find(
    group => group.storages.some(storage => storage.storageKey === pal.value.storageKey),
  );
  activeGroupKey.value = (sourceGroup?.storages.length > 1
    ? sourceGroup
    : groups.value.find(group => group.selected) ?? groups.value[0])?.key ?? "";
  await nextTick();
  dialog.value?.focus();
  window.addEventListener("resize", schedulePreviewScale);
});

// One request per target in the group on screen, and only the first time it is
// opened -- the answers are about this Pal and are kept for as long as it is the
// one being moved.
watch(activeGroup, group => {
  if (group) palStore.loadMoveTargets(group.storages.map(storage => storage.storageKey));
}, { immediate: true });

watch(
  () => storagesStore.conflictTarget,
  async target => {
    if (!target) return;
    await nextTick();
    schedulePreviewScale();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  if (previewFrame) cancelAnimationFrame(previewFrame);
  window.removeEventListener("resize", schedulePreviewScale);
});
</script>

<template>
  <Teleport to="body">
    <div class="move-dialog-layer editor-modal-overlay" @pointerdown.self="closeDialog" @keydown.esc="closeDialog">
      <section ref="dialog" :class="['move-dialog', 'editor-glass-surface', { 'has-conflict': conflict }]" role="dialog" aria-modal="true"
        aria-labelledby="move-dialog-title" tabindex="-1">
        <header>
          <div>
            <h2 id="move-dialog-title">{{ palStore.getTranslatedText('Editor_Move_Dialog_Title') }}</h2>
            <p>{{ palStore.getTranslatedText('Editor_Move_Dialog_Subtitle') }}</p>
          </div>
          <button type="button" class="move-dialog__close" :aria-label="palStore.getTranslatedText('Message_Close')"
            @click="closeDialog">×</button>
        </header>

        <div v-if="!conflict" class="move-dialog__panes">
          <section class="move-dialog__pane">
            <h3>{{ palStore.getTranslatedText('Editor_Move_Groups') }}</h3>
            <OverlayScrollArea>
              <div class="move-dialog__groups overlay-scroll-area__viewport" role="listbox"
                :aria-label="palStore.getTranslatedText('Editor_Move_Groups')">
                <button v-for="group in groups" :key="group.key" type="button" role="option"
                  :aria-selected="group.key === activeGroup?.key"
                  :class="{ 'is-active': group.key === activeGroup?.key, 'is-current-player': group.selected }"
                  @click="activeGroupKey = group.key">
                  <span>{{ groupLabel(group) }}</span>
                  <small v-if="group.selected">{{ palStore.getTranslatedText('Editor_Move_Current_Player') }}</small>
                </button>
              </div>
            </OverlayScrollArea>
          </section>

          <section class="move-dialog__pane">
            <h3>{{ palStore.getTranslatedText('Editor_Move_Containers') }}</h3>
            <OverlayScrollArea>
              <div class="move-dialog__containers overlay-scroll-area__viewport" role="listbox"
                :aria-label="palStore.getTranslatedText('Editor_Move_Containers')">
                <button v-for="storage in activeGroup?.storages || []" :key="storage.storageKey" type="button"
                  role="option" :aria-selected="storage.storageKey === pendingStorageKey"
                  :aria-disabled="!isOffered(storage)"
                  :class="{ 'is-active': storage.storageKey === pendingStorageKey }"
                  @click="selectStorage(storage)">
                  <span class="move-dialog__container-copy">
                    <strong>{{ storageLabel(storage) }}</strong>
                    <small v-if="disabledReasonKey(storage)">
                      {{ palStore.getTranslatedText(disabledReasonKey(storage)) }}
                    </small>
                  </span>
                  <span class="move-dialog__capacity">{{ storage.occupied }}/{{ storage.capacity }}</span>
                </button>
                <p v-if="!activeGroup?.storages?.length" class="move-dialog__empty">
                  {{ palStore.getTranslatedText('Editor_Move_No_Containers') }}
                </p>
              </div>
            </OverlayScrollArea>
          </section>
        </div>

        <section v-else class="move-dialog__conflict">
          <h3>{{ palStore.getTranslatedText('Editor_Transfer_Conflict_Title') }}</h3>
          <p>{{ palStore.getTranslatedText('Editor_Transfer_Conflict_Subtitle') }}</p>
          <div class="move-dialog__locked-target">
            <span>{{ palStore.getTranslatedText('Editor_Move_Target') }}</span>
            <strong>{{ conflictTargetLabel }}</strong>
          </div>
        </section>

        <footer>
          <button type="button" @click="closeDialog">{{ palStore.getTranslatedText('AddPal_Cancel') }}</button>
          <template v-if="conflict">
            <button type="button" :disabled="!storagesStore.conflictTarget" @click="jumpToPal">
              {{ palStore.getTranslatedText('Editor_Transfer_Jump') }}
            </button>
            <span ref="updateAction" class="move-dialog__update-action" @pointerenter="schedulePreviewScale"
              @focusin="schedulePreviewScale">
              <button type="button" class="move-dialog__update" :disabled="!storagesStore.conflictTarget"
                @click="updatePal">{{ palStore.getTranslatedText('Editor_Transfer_Update') }}</button>
            </span>
          </template>
          <button v-else type="button" class="move-dialog__confirm" :disabled="!pendingStorageKey"
            @click="movePal">{{ palStore.getTranslatedText(isGlobalTransfer ? 'Editor_Transfer_Clone' : 'Editor_Move_Pal') }}</button>
        </footer>
      </section>
      <div v-if="storagesStore.conflictTarget" ref="preview" class="move-dialog__preview" role="tooltip"
        :style="previewStyle">
        <PalBriefPanel :data="conflict.incoming" :changed-fields="conflict.fieldChanges" tone="incoming"
          :title="palStore.getTranslatedText('Editor_Transfer_Incoming')" />
        <span class="move-dialog__comparison-arrow" aria-hidden="true" />
        <PalBriefPanel :data="conflict.existing" :changed-fields="conflict.fieldChanges" tone="existing"
          :title="palStore.getTranslatedText('Editor_Transfer_Existing')" />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.move-dialog-layer {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  padding: var(--editor-space-4);
}

.move-dialog {
  position: relative;
  display: grid;
  height: min(44rem, calc(100dvh - 2rem));
  width: min(52rem, calc(100vw - 2rem));
  max-height: calc(100dvh - 2rem);
  grid-template-rows: auto minmax(0, 1fr) auto;
  box-sizing: border-box;
  gap: var(--editor-space-3);
  padding: var(--editor-space-4);
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
}
.move-dialog.has-conflict { height: auto; overflow: visible; }

header,
footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--editor-space-3);
}

h2,
h3,
p { margin: 0; }
header p { color: var(--editor-color-muted); }

button {
  min-height: var(--editor-control-height);
  border: 1px solid var(--editor-color-border);
  border-radius: var(--editor-radius-sm);
  color: var(--editor-color-text);
  background: var(--editor-color-control);
  cursor: pointer;
}

.move-dialog__close { min-width: var(--editor-control-height); font-size: 1.25rem; }
.move-dialog__panes { display: grid; min-height: 0; grid-template-columns: minmax(12rem, .75fr) minmax(18rem, 1.25fr); gap: var(--editor-space-2); }
.move-dialog__pane { display: grid; min-height: 0; grid-template-rows: auto minmax(0, 1fr); gap: var(--editor-space-2); padding: var(--editor-space-2); overflow: hidden; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); background: var(--editor-color-surface-subtle); }
.move-dialog__pane h3 { color: var(--editor-color-muted); font-size: .8rem; }
.move-dialog__groups,
.move-dialog__containers { display: flex; min-height: 0; flex-direction: column; gap: var(--editor-space-1); overflow-y: auto; }

.move-dialog__groups button,
.move-dialog__containers button { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: var(--editor-space-2); padding: var(--editor-space-2) var(--editor-space-3); text-align: left; }
.move-dialog__groups button { min-height: 3rem; }
.move-dialog__groups button small { color: var(--editor-color-primary); }
.move-dialog__groups button.is-current-player { border-left: .2rem solid var(--editor-color-primary); }
.move-dialog__container-copy { display: grid; min-width: 0; }
.move-dialog__container-copy strong,
.move-dialog__container-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.move-dialog__container-copy small { color: var(--editor-color-warning); }
.move-dialog__capacity { flex: 0 0 auto; color: var(--editor-color-muted); font-variant-numeric: tabular-nums; }

.move-dialog__groups button:hover,
.move-dialog__groups button.is-active,
.move-dialog__containers button:not([aria-disabled='true']):hover,
.move-dialog__containers button.is-active { border-color: var(--editor-color-focus); color: var(--editor-color-background); background: var(--editor-color-primary); }
.move-dialog__groups button:hover small,
.move-dialog__groups button.is-active small,
.move-dialog__containers button:not([aria-disabled='true']):hover .move-dialog__capacity,
.move-dialog__containers button.is-active .move-dialog__capacity { color: var(--editor-color-background); }
.move-dialog__containers button[aria-disabled='true'] { border-color: var(--editor-color-disabled); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); cursor: not-allowed; }
.move-dialog__containers button[aria-disabled='true']:hover,
.move-dialog__containers button[aria-disabled='true']:focus-visible { border-color: var(--editor-color-warning); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); }
.move-dialog__containers button[aria-disabled='true'] .move-dialog__capacity { color: var(--editor-color-muted); }
.move-dialog__empty { padding: var(--editor-space-4); color: var(--editor-color-muted); text-align: center; }
.move-dialog__conflict { display: grid; min-height: 11rem; place-content: center; gap: var(--editor-space-2); padding: var(--editor-space-5); text-align: center; }
.move-dialog__conflict h3 { color: var(--editor-color-warning); font-size: 1.1rem; }
.move-dialog__conflict p { color: var(--editor-color-muted); }
.move-dialog__locked-target { display: grid; margin-top: var(--editor-space-2); gap: .25rem; }
.move-dialog__locked-target span { color: var(--editor-color-muted); font-size: .75rem; }

footer { position: relative; justify-content: flex-end; }
footer button { padding: 0 var(--editor-space-4); }
.move-dialog__confirm { border-color: var(--editor-color-primary); color: var(--editor-color-background); background: var(--editor-color-primary); }
.move-dialog__update-action { position: relative; }
.move-dialog__update { height: 100%; padding: 0 var(--editor-space-4); border-color: var(--editor-color-danger, #dc4655); color: #fff; background: var(--editor-color-danger, #b92f3d); }
.move-dialog-layer > .move-dialog__preview {
  position: absolute;
  z-index: 5;
  top: var(--editor-space-4);
  left: 50%;
  display: grid;
  width: min(66rem, calc(100vw - 3rem));
  box-sizing: border-box;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  justify-items: center;
  gap: var(--editor-space-4);
  padding: var(--editor-space-4);
  overflow: visible;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-lg);
  background: var(--editor-color-glass-toolbar);
  -webkit-backdrop-filter: var(--editor-glass-filter);
  backdrop-filter: var(--editor-glass-filter);
  box-shadow: var(--editor-glass-shadow);
  opacity: 0;
  transform: translateX(-50%) scale(var(--move-preview-scale, 1));
  transform-origin: top center;
  visibility: hidden;
  pointer-events: none;
}
.move-dialog-layer:has(.move-dialog__update-action:hover) > .move-dialog__preview,
.move-dialog-layer:has(.move-dialog__update-action:focus-within) > .move-dialog__preview {
  opacity: 1;
  visibility: visible;
}
.move-dialog__comparison-arrow {
  position: relative;
  display: grid;
  width: 2.75rem;
  height: 2.75rem;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--editor-color-primary) 55%, var(--editor-color-glass-border));
  border-radius: 999px;
  background: color-mix(in srgb, var(--editor-color-primary) 16%, var(--editor-color-control));
  box-shadow: var(--editor-shadow-compact);
}
.move-dialog__comparison-arrow::before {
  width: 1.15rem;
  height: .12rem;
  content: '';
  border-radius: 999px;
  background: var(--editor-color-primary);
}
.move-dialog__comparison-arrow::after {
  position: absolute;
  width: .5rem;
  height: .5rem;
  content: '';
  border-top: .12rem solid var(--editor-color-primary);
  border-right: .12rem solid var(--editor-color-primary);
  transform: translateX(.32rem) rotate(45deg);
}
.move-dialog__confirm:disabled { border-color: var(--editor-color-disabled); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); cursor: not-allowed; }
button:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 2px; }

@media (max-width: 700px) {
  .move-dialog { overflow: hidden; }
  .move-dialog__panes { grid-template-columns: 1fr; grid-template-rows: repeat(2, minmax(0, 1fr)); }
  .move-dialog__pane { min-height: 0; }
  .move-dialog-layer > .move-dialog__preview {
    top: var(--editor-space-2);
    width: calc(100vw - 2rem);
    grid-template-columns: 1fr;
  }
  .move-dialog__comparison-arrow { transform: rotate(90deg); }
}
</style>
