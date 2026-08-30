// The move dialog's two questions, answered from what the backend sent.
//
// Which places to show and in what order is `buildStorageMoveGroups`: a storage
// carries the group it belongs to, that group's heading and both orderings
// (spec §8.2), so nothing here decides that a Global Palbox deserves its own
// heading or that a container with no owner belongs under "other".
//
// Why a place is not offered is `moveReasonKey`: the reason is a stable business
// code from `GET .../pal-transfer-capability`, and this only says which existing
// message shows it. The dialog cannot reach a different verdict from the backend
// any more, because it no longer forms one.

// Everything that means "this target cannot take a Pal right now" -- an owner or
// guild the save no longer has, a Global Palbox that is not loaded, a target that
// went away -- shares the message the dialog has always shown for a target it
// cannot use. Only reasons the user can do something different about get their own.
const MOVE_REASON_KEYS = Object.freeze({
  ALREADY_IN_TARGET: "Editor_Move_Reason_Current",
  TARGET_FULL: "Editor_Move_Reason_Full",
  DUPLICATE_IN_TARGET: "Editor_Move_Reason_Duplicate",
  CROSS_GUILD_UNSUPPORTED: "Editor_Move_Reason_DifferentGuild",
  OWNER_REQUIRED: "Editor_Move_Reason_OwnerRequired",
  GPS_PLAYER_TARGET_REQUIRED: "Editor_Move_Reason_GpsPlayerRequired",
});

export const MOVE_REASON_FALLBACK_KEY = "Editor_Move_Reason_Unsafe";

export function moveReasonKey(reason) {
  if (!reason) return null;
  return MOVE_REASON_KEYS[reason] ?? MOVE_REASON_FALLBACK_KEY;
}

// `activePlayerGroupKey` is the group of the player whose list is open, marked so
// the user can find where they came from. A group's `label` is null where the
// heading is the frontend's own translated text, the same rule `GET /api/rosters`
// follows.
export function buildStorageMoveGroups(storages, activePlayerGroupKey) {
  const groups = new Map();
  for (const storage of storages ?? []) {
    let group = groups.get(storage.navigationGroupKey);
    if (!group) {
      group = {
        key: storage.navigationGroupKey,
        label: storage.navigationGroupLabel,
        order: storage.navigationGroupOrder,
        selected: storage.navigationGroupKey === activePlayerGroupKey,
        storages: [],
      };
      groups.set(group.key, group);
    }
    group.storages.push(storage);
  }

  const rows = [...groups.values()];
  for (const group of rows) group.storages.sort((left, right) => left.order - right.order);
  return rows.sort((left, right) => left.order - right.order);
}
