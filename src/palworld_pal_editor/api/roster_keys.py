"""What a roster is called on each side of the API boundary.

Both sides name the fixed rosters the same way. The one difference is a player
roster: `player:<uid>` over HTTP, and the bare uid inside `SaveManager`, which
identifies a player by uid and has no reason to know the URL prefix. This is the
one place that difference is spelled out, and the one place that says which list a
record turns up in. It exists as its own module because `pals`, `rosters` and
`storages` all need it and `rosters` already reads `pals`.
"""

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_record import PalRecord

PLAYER_ROSTER_PREFIX = "player:"

# Rosters that are one fixed place rather than one player. `unrostered` has no entry
# in the `GET /api/rosters` listing because no UI control opens it; it stays
# addressable because it is the only way to see a Pal that every other roster disowns.
UNROSTERED = "unrostered"

FIXED_ROSTERS = frozenset({"base-workers", "global-palbox", UNROSTERED})


def roster_key_for_target(descriptor: dict, owner_uid) -> str:
    """The list a Pal turns up in once it is standing in this storage.

    The storage answers it wherever the storage is a place rather than a person: the
    Global Palbox and a base camp's container belong to no player. Everywhere else the
    Pal's own owner decides -- and an unowned Pal anywhere else is in no list at all,
    which is a real answer for a Pal being moved and a refusal for one being created.
    """
    if descriptor["StorageKind"] == "global_palbox":
        return "global-palbox"
    if descriptor["ContainerKind"] == "base":
        return "base-workers"
    return f"{PLAYER_ROSTER_PREFIX}{owner_uid}" if owner_uid else UNROSTERED


def core_roster_key(roster_key: str) -> str:
    """The name `SaveManager` knows this roster by: a fixed roster keeps its own."""
    return roster_key.removeprefix(PLAYER_ROSTER_PREFIX)


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
    working = {item.record_key for item in manager.rosters.working_records()}
    return "base-workers" if record.record_key in working else "unrostered"
