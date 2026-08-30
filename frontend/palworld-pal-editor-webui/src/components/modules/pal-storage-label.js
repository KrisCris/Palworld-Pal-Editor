// What one storage is called (spec §8.2).
//
// The backend sends the name in two halves. `label` is the data half -- a player's
// nickname, a base camp's name, null where there is none -- and `labelKey` with
// `labelArgs` names the translated half. Composing them here is what lets the
// dialog say "Alice · Palbox" in the user's language without the frontend deciding
// what a storage *is* from its kind, which is the branching spec §8.2 removes.
//
// A missing storage is a Pal that does not occupy the slot it records for itself,
// which is the one thing this can be asked about that has no name of its own.

export function formatStorageLabel(storage, translate) {
  if (!storage) return translate("Editor_Container_Anomaly");

  const kind = storage.labelKey
    ? translate(storage.labelKey, storage.labelArgs ?? [])
    : "";
  if (storage.label && kind) return `${storage.label} · ${kind}`;
  return kind || storage.label || storage.storageKey || "";
}
