// What every Pal write answers with, and the one place that acts on it (spec §10).
//
// The backend returns `{resultRecord, deletedRecordKeys, affectedRosterKeys,
// affectedStorageKeys}` from anything that changes a Pal, a roster or a storage
// (spec §8.3). Before this, each caller guessed: whether the source Pal was still
// there after a move, which list a new Pal had landed in, whether the selection
// was still valid. Those guesses were how a Pal ended up in two lists at once.
//
// This holds no state of its own -- the Pal cache is `stores/pals` and the lists
// are `stores/rosters`; it only tells them what the backend just said.

import { usePalsStore } from "./pals.js";
import { useRostersStore } from "./rosters.js";

export async function applyOperationResult(result) {
    const pals = usePalsStore();
    const rosters = useRostersStore();

    if (result.resultRecord) pals.applyDetail(result.resultRecord);
    // A delete is the only operation that names one today, and it has no result
    // record to point at, so `forget` clearing the selection is the whole answer.
    // A relocate answers with a new key for the same Pal and deletes the old
    // one; S4a adds the selection migration §10 describes along with it.
    for (const recordKey of result.deletedRecordKeys) pals.forget(recordKey);

    // Only the list on screen is re-read. The rest are dropped and re-read the
    // next time they are opened, which is also what stops a heal-all from
    // fetching every roster in the save.
    for (const rosterKey of result.affectedRosterKeys) {
        if (rosterKey === rosters.activeRosterKey) await rosters.loadRosterPals(rosterKey);
        else rosters.invalidate(rosterKey);
    }
    return result;
}
