<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

import PalBriefPanel from "@/components/modules/PalBriefPanel.vue";
import {
  buildContainerMoveGroups,
  containerMoveDisabledReason,
} from "@/components/modules/pal-container-move";
import { formatContainerLabel } from "@/components/modules/pal-container-label";
import { usePalEditorStore } from "@/stores/paleditor";

const emit = defineEmits(["close"]);
const palStore = usePalEditorStore();
const dialog = ref(null);
const activeGroupKey = ref("");
const pendingContainerId = ref("");
const conflict = computed(() => palStore.PAL_TRANSFER_CONFLICT);

const groups = computed(() => buildContainerMoveGroups(
  palStore.PAL_CONTAINERS,
  [...palStore.PLAYER_MAP.values()],
  palStore.SELECTED_PLAYER_ID,
));
const activeGroup = computed(() => (
  groups.value.find(group => group.key === activeGroupKey.value) ?? groups.value[0]
));
const reasonKey = Object.freeze({
  current: "Editor_Move_Reason_Current",
  full: "Editor_Move_Reason_Full",
  unsafe: "Editor_Move_Reason_Unsafe",
  different_guild: "Editor_Move_Reason_DifferentGuild",
  owner_required: "Editor_Move_Reason_OwnerRequired",
});
const groupLabel = group => group.label || palStore.getTranslatedText(
  group.kind === "bases" ? "Editor_Move_Group_Bases" : "Editor_Move_Group_Other",
);
const containerLabel = container => formatContainerLabel(
  container,
  palStore.getTranslatedText,
);
const disabledReason = container => containerMoveDisabledReason(
  container,
  palStore.SELECTED_PAL_DATA,
);
const pendingContainer = computed(() => palStore.PAL_CONTAINERS.find(
  container => container.StorageKey === pendingContainerId.value,
));
const isGlobalTransfer = computed(() => (
  palStore.SELECTED_PAL_DATA?.StorageKind === "global_palbox"
  || pendingContainer.value?.StorageKind === "global_palbox"
));

function selectContainer(container) {
  if (disabledReason(container)) return;
  pendingContainerId.value = container.StorageKey;
}

async function movePal() {
  if (!pendingContainerId.value) return;
  if (await palStore.movePal(pendingContainerId.value)) return closeDialog();
  if (conflict.value?.LockedTarget) {
    pendingContainerId.value = conflict.value.Candidates?.find(
      candidate => candidate.RecordKey === conflict.value.LockedTarget,
    )?.StorageKey || pendingContainerId.value;
  }
}

async function updatePal() {
  if (await palStore.updateConflictingPal()) closeDialog();
}

async function jumpToPal() {
  if (await palStore.jumpToConflictingPal()) closeDialog(false);
}

function closeDialog(clearConflict = true) {
  if (clearConflict) palStore.clearPalTransferConflict();
  emit("close");
}

onMounted(async () => {
  palStore.clearPalTransferConflict();
  const current = palStore.PAL_CONTAINERS.find(
    container => container.StorageKey === palStore.SELECTED_PAL_DATA.StorageKey,
  );
  activeGroupKey.value = current?.StorageKind === "global_palbox"
    ? groups.value.find(group => group.kind === "player")?.key || "global_palbox"
    : current?.ContainerKind === "base"
      ? "bases"
      : current?.OwnerPlayerUId || "other";
  await nextTick();
  dialog.value?.focus();
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
            <div class="move-dialog__groups" role="listbox" :aria-label="palStore.getTranslatedText('Editor_Move_Groups')">
              <button v-for="group in groups" :key="group.key" type="button" role="option"
                :aria-selected="group.key === activeGroup?.key"
                :class="{ 'is-active': group.key === activeGroup?.key, 'is-current-player': group.selected }"
                @click="activeGroupKey = group.key">
                <span>{{ groupLabel(group) }}</span>
                <small v-if="group.selected">{{ palStore.getTranslatedText('Editor_Move_Current_Player') }}</small>
              </button>
            </div>
          </section>

          <section class="move-dialog__pane">
            <h3>{{ palStore.getTranslatedText('Editor_Move_Containers') }}</h3>
            <div class="move-dialog__containers" role="listbox" :aria-label="palStore.getTranslatedText('Editor_Move_Containers')">
              <button v-for="container in activeGroup?.containers || []" :key="container.StorageKey" type="button"
                role="option" :aria-selected="container.StorageKey === pendingContainerId"
                :aria-disabled="Boolean(disabledReason(container))"
                :class="{ 'is-active': container.StorageKey === pendingContainerId }"
                @click="selectContainer(container)">
                <span class="move-dialog__container-copy">
                  <strong>{{ containerLabel(container) }}</strong>
                  <small v-if="disabledReason(container)">
                    {{ palStore.getTranslatedText(reasonKey[disabledReason(container)]) }}
                  </small>
                </span>
                <span class="move-dialog__capacity">{{ container.Occupied }}/{{ container.Size }}</span>
              </button>
              <p v-if="!activeGroup?.containers?.length" class="move-dialog__empty">
                {{ palStore.getTranslatedText('Editor_Move_No_Containers') }}
              </p>
            </div>
          </section>
        </div>

        <section v-else class="move-dialog__conflict">
          <h3>{{ palStore.getTranslatedText('Editor_Transfer_Conflict_Title') }}</h3>
          <p>{{ palStore.getTranslatedText('Editor_Transfer_Conflict_Subtitle') }}</p>
          <div class="move-dialog__locked-target">
            <span>{{ palStore.getTranslatedText('Editor_Move_Target') }}</span>
            <strong>{{ conflict.Candidates?.[0]?.ContainerLabel }}</strong>
          </div>
        </section>

        <footer>
          <button type="button" @click="closeDialog">{{ palStore.getTranslatedText('AddPal_Cancel') }}</button>
          <template v-if="conflict">
            <button type="button" :disabled="!conflict.LockedTarget || palStore.LOADING_FLAG" @click="jumpToPal">
              {{ palStore.getTranslatedText('Editor_Transfer_Jump') }}
            </button>
            <span class="move-dialog__update-action">
              <button type="button" class="move-dialog__update" :disabled="!conflict.LockedTarget || palStore.LOADING_FLAG"
                @click="updatePal">{{ palStore.getTranslatedText('Editor_Transfer_Update') }}</button>
              <span v-if="conflict.LockedTarget" class="move-dialog__preview" role="tooltip">
                <PalBriefPanel :data="conflict.Incoming" :changed-fields="conflict.FieldChanges"
                  :title="palStore.getTranslatedText('Editor_Transfer_Incoming')" />
                <PalBriefPanel :data="conflict.Existing" :changed-fields="conflict.FieldChanges"
                  :title="palStore.getTranslatedText('Editor_Transfer_Existing')" />
              </span>
            </span>
          </template>
          <button v-else type="button" class="move-dialog__confirm" :disabled="!pendingContainerId || palStore.LOADING_FLAG"
            @click="movePal">{{ palStore.getTranslatedText(isGlobalTransfer ? 'Editor_Transfer_Clone' : 'Editor_Move_Pal') }}</button>
        </footer>
      </section>
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
  width: min(52rem, calc(100vw - 2rem));
  max-height: calc(100dvh - 2rem);
  box-sizing: border-box;
  gap: var(--editor-space-3);
  padding: var(--editor-space-4);
  overflow: hidden;
  border: 1px solid var(--editor-color-glass-border);
  border-radius: var(--editor-radius-md);
}
.move-dialog.has-conflict { overflow: visible; }

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
.move-dialog__pane { display: grid; min-height: 18rem; grid-template-rows: auto minmax(0, 1fr); gap: var(--editor-space-2); padding: var(--editor-space-2); overflow: hidden; border: 1px solid var(--editor-color-border); border-radius: var(--editor-radius-sm); background: var(--editor-color-surface-subtle); }
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

footer { justify-content: flex-end; }
footer button { padding: 0 var(--editor-space-4); }
.move-dialog__confirm { border-color: var(--editor-color-primary); color: var(--editor-color-background); background: var(--editor-color-primary); }
.move-dialog__update-action { position: relative; }
.move-dialog__update { height: 100%; padding: 0 var(--editor-space-4); border-color: var(--editor-color-danger, #dc4655); color: #fff; background: var(--editor-color-danger, #b92f3d); }
.move-dialog__preview { display: none; position: absolute; z-index: 5; right: 0; bottom: calc(100% - 6rem); width: min(42rem, calc(100vw - 3rem)); grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--editor-space-2); pointer-events: none; }
.move-dialog__update-action:hover .move-dialog__preview,
.move-dialog__update-action:focus-within .move-dialog__preview { display: grid; }
.move-dialog__confirm:disabled { border-color: var(--editor-color-disabled); color: var(--editor-color-muted); background: var(--editor-color-surface-subtle); cursor: not-allowed; }
button:focus-visible { outline: 2px solid var(--editor-color-focus); outline-offset: 2px; }

@media (max-width: 700px) {
  .move-dialog { overflow-y: auto; }
  .move-dialog__panes { grid-template-columns: 1fr; }
  .move-dialog__pane { min-height: 10rem; max-height: 32vh; }
  .move-dialog__preview { width: calc(100vw - 2rem); grid-template-columns: 1fr; max-height: 70vh; overflow: auto; }
}
</style>
