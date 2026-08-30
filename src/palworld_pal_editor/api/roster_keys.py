"""What a roster is called on each side of the API boundary (spec §8.2).

`GET /api/rosters` answers in `player:<uid>` / `base-workers` / `global-palbox`;
`SaveManager` still answers in the old UI's button ids. This is the one place that
translation happens, and the one place that says which list a record turns up in.
It exists as its own module because `pals`, `rosters` and `storages` all need it
and `rosters` already reads `pals`. S4a deletes `legacy_roster_id` when the create
and duplicate chains it feeds start speaking the API's own vocabulary.
"""

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_record import PalRecord

PLAYER_ROSTER_PREFIX = "player:"

# Rosters that are one fixed place rather than one player, mapped to the name
# SaveManager still knows them by. `unrostered` has no entry in the `GET /api/rosters`
# listing because no UI control opens it; it stays addressable because it is the only
# way to see a Pal that every other roster disowns.
FIXED_ROSTERS = {
    "base-workers": "PAL_BASE_WORKER_BTN",
    "global-palbox": "PAL_GLOBAL_STORAGE_BTN",
    "unrostered": "PAL_OTHER_PAL_BTN",
}


def legacy_roster_id(roster_key: str) -> str:
    """The button id `creation_targets`, `create_pal` and `duplicate_pal` still take."""
    return FIXED_ROSTERS.get(roster_key, roster_key.removeprefix(PLAYER_ROSTER_PREFIX))


def roster_key_for_record(manager: SaveManager, record: PalRecord) -> str:
    """The one list this record appears in.

    The inverse of `SaveManager.records_for_roster`, and every record has exactly one
    answer: the Global Palbox is a place, an owned Pal belongs to its owner wherever
    it is standing, an unowned Pal in a camp's container is a base worker, and what
    no list claims is unrostered. An operation says which lists it disturbed by
    asking this about the records it touched, rather than by trusting the client to
    say which list it happened to have open.
    """
    if record.storage_kind == "global_palbox":
        return "global-palbox"
    owner = manager.get_player(record.pal.OwnerPlayerUId)
    if owner is not None:
        return f"{PLAYER_ROSTER_PREFIX}{owner.PlayerUId}"
    working = {item.record_key for item in manager.working_records()}
    return "base-workers" if record.record_key in working else "unrostered"
