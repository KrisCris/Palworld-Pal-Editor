// Where a Pal can be, and what moving one there would mean.
//
// Two different questions live here and they are deliberately not the same one.
// `storages` is the directory: every place in the save, what it is called and how
// full it is. It says nothing about a particular Pal. Whether *this* Pal may go to
// *that* place is `capability`, which is asked of the backend per pair -- because
// the answer turns on the Pal's guild, its owner, whether the target already holds
// its identity and whether the Pal is standing where it says it is, none of which
// a storage knows about itself.
//
// The dialog decides neither from a storage kind: doing so disagrees with the
// backend often enough that a move gets offered and then refused. The component
// renders the answer it was given.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { ApiError } from "../api/http.js";
import { listPalCreationTargets } from "../api/rosters.js";
import {
    createPalTransfer,
    getPalTransferCapability,
    listStorages,
} from "../api/storages.js";
import { useBackendStore } from "./backend.js";
import { applyOperationResult } from "./operation-result.js";
import { usePalsStore } from "./pals.js";
import { gated, useSessionStore } from "./session.js";

export const useStoragesStore = defineStore("storages", () => {
    const backend = useBackendStore();
    const session = useSessionStore();
    const pals = usePalsStore();

    const storages = ref([]);
    // Capabilities are about one source Pal, so they are dropped whole when the
    // Pal changes rather than filtered: a stale `allowed` is how a move gets
    // offered for a Pal it was never asked about.
    const capabilities = ref(new Map());
    const capabilitySource = ref(null);
    // The conflict payload, held from the 409 that raised it until the user
    // answers it or closes the dialog.
    const conflict = ref(null);

    const byKey = computed(() => new Map(
        storages.value.map(storage => [storage.storageKey, storage]),
    ));
    const storage = storageKey => byKey.value.get(storageKey) ?? null;
    // A base camp is worth listing even before anybody works in it, which the
    // roster listing alone cannot say.
    const hasBaseStorage = computed(() => storages.value.some(
        item => item.navigationGroupKey === "bases",
    ));

    async function load() {
        const epoch = session.sessionEpoch;
        const rows = await listStorages(session.readOptions());
        if (!session.isCurrentSession(epoch)) return false;
        storages.value = rows;
        return true;
    }

    // Occupancy changed under a directory that is otherwise still correct, so the
    // whole of it is re-read rather than each named storage: it is one request
    // either way and the answer is generated per call on the backend.
    async function refresh(storageKeys) {
        if (!storageKeys.length) return true;
        return load();
    }

    const capability = storageKey => capabilities.value.get(storageKey) ?? null;

    // Every target in one group at once, because that is what the dialog shows at
    // once. Asking about the whole save would be dozens of requests for rows
    // nobody has scrolled to.
    async function loadCapabilities(sourceRecordKey, storageKeys) {
        if (capabilitySource.value !== sourceRecordKey) {
            capabilitySource.value = sourceRecordKey;
            capabilities.value = new Map();
        }
        const missing = storageKeys.filter(key => !capabilities.value.has(key));
        if (!missing.length) return true;
        const epoch = session.sessionEpoch;
        const answers = await Promise.all(missing.map(
            key => getPalTransferCapability(key, sourceRecordKey, session.readOptions()),
        ));
        if (!session.isCurrentSession(epoch)
            || capabilitySource.value !== sourceRecordKey) return false;
        const next = new Map(capabilities.value);
        missing.forEach((key, index) => next.set(key, answers[index]));
        capabilities.value = next;
        return true;
    }

    // Which targets the move dialog may offer for the Pal on screen, for the one
    // group being looked at.
    async function loadMoveTargets(storageKeys) {
        try {
            return await loadCapabilities(pals.selectedRecordKey, storageKeys);
        } catch (error) {
            backend.reportApiFailure(error, "Operation_Move_Pal");
            return false;
        }
    }

    function clearCapabilities() {
        capabilities.value = new Map();
        capabilitySource.value = null;
    }

    function clearConflict() {
        conflict.value = null;
    }

    // The one Pal an overwrite would land on, once the backend has named exactly
    // one. With several candidates it has no basis for choosing and neither has
    // this store, so the dialog offers nothing to confirm.
    const conflictTarget = computed(() => (
        conflict.value?.candidates?.length === 1 ? conflict.value.candidates[0] : null
    ));

    async function submitTransfer(body) {
        clearConflict();
        try {
            return await applyOperationResult(await createPalTransfer(body));
        } catch (error) {
            if (!(error instanceof ApiError)
                || error.code !== "PAL_IDENTITY_CONFLICT") throw error;
            // Not a failure: the destination already holds this identity and the
            // user is the one who decides whether to overwrite it.
            conflict.value = {
                ...error.details,
                sourceRecordKey: body.sourceRecordKey,
                targetStorageKey: body.targetStorageKey,
            };
            return null;
        }
    }

    // `null` means the backend asked a question -- see `conflict` -- rather than
    // that anything went wrong. A real failure throws.
    function movePal(targetStorageKey) {
        return submitTransfer({
            sourceRecordKey: pals.selectedRecordKey,
            targetStorageKey,
        });
    }

    // The confirmation of an overwrite, naming the Pal the user was actually
    // shown. The backend re-checks that it is still that Pal, because the dialog
    // was open while the save was not held.
    function overwriteConflictTarget() {
        const target = conflictTarget.value;
        if (!target) return null;
        return submitTransfer({
            sourceRecordKey: conflict.value.sourceRecordKey,
            targetStorageKey: conflict.value.targetStorageKey,
            conflictResolution: {
                expectedTarget: {
                    recordKey: target.recordKey,
                    storageKey: target.storageKey,
                },
            },
        });
    }

    function creationTargets(rosterKey) {
        return listPalCreationTargets(rosterKey, session.readOptions());
    }

    function clear() {
        storages.value = [];
        clearCapabilities();
        clearConflict();
    }

    return {
        storages,
        conflict,
        conflictTarget,
        hasBaseStorage,
        storage,
        capability,
        load,
        refresh,
        loadCapabilities,
        clearCapabilities,
        ...gated(session, { loadMoveTargets }),
        clearConflict,
        movePal,
        overwriteConflictTarget,
        creationTargets,
        clear,
    };
});
