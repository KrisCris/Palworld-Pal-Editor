// What every Pal write answers with, and the one place that acts on it.
//
// The backend returns `{resultRecord, deletedRecordKeys, affectedRosterKeys,
// affectedStorageKeys}` from anything that changes a Pal, a roster or a storage.
// No caller infers any of it -- whether the source Pal survived a move, which
// list a new one landed in, whether the selection is still valid. Inferring it is
// how the same Pal ends up in two lists at once.
//
// This holds no state of its own -- the Pal cache is `stores/pals`, the lists are
// `stores/rosters` and the storage directory is `stores/storages`; it only tells
// them what the backend just said.

import { usePalsStore } from "./pals.js";
import { useRostersStore } from "./rosters.js";
import { useStoragesStore } from "./storages.js";

export async function applyOperationResult(result) {
    const pals = usePalsStore();
    const rosters = useRostersStore();
    const storages = useStoragesStore();

    const wasSelected = pals.selectedRecordKey;
    if (result.resultRecord) pals.applyDetail(result.resultRecord);
    for (const recordKey of result.deletedRecordKeys) pals.forget(recordKey);
    // A relocate answers with a new key for the same Pal and deletes the old one.
    // The selection follows it: the Pal on screen did not go anywhere, only its
    // address did. Only a real deletion -- one with no result record to point at
    // -- leaves the selection cleared, which `forget` has already done.
    if (result.resultRecord && result.deletedRecordKeys.includes(wasSelected)) {
        pals.reselect(result.resultRecord.recordKey);
    }

    // Only the list on screen is re-read. The rest are dropped and re-read the
    // next time they are opened, which is also what stops a heal-all from
    // fetching every roster in the save.
    for (const rosterKey of result.affectedRosterKeys) {
        if (rosterKey === rosters.activeRosterKey) await rosters.loadRosterPals(rosterKey);
        else rosters.invalidate(rosterKey);
    }
    // Capacity is what the move dialog reads off a storage, and an operation that
    // named one changed how full it is.
    await storages.refresh(result.affectedStorageKeys);
    return result;
}
