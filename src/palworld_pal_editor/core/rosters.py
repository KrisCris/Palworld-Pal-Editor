"""Which Pals a roster lists, and the order the Pal list shows them in.

A roster is a question asked of the records, never a stored list. Nothing here
maintains membership: every answer is derived on the call, from the repository's
indexes and -- for base workers -- from the camps. The alternative, a
hand-maintained set of record keys, has to be re-filed by every create, move and
transfer, and forgetting to do so was silent and left a list pointing at the
previous owner.

`base-workers`, `global-palbox` and `unrostered` name themselves; any other key
is a player's uid.
"""

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.utils import alphanumeric_key


def paldeck_display_key(pal: PalEntity) -> tuple:
    """The Pal list's display order, unchanged from when it lived on PlayerEntity.

    It reads nothing but the Pal itself, so it sorts a roster of records as happily
    as it sorted a palbox of entities.
    """
    return (
        pal.IsHuman or False,
        alphanumeric_key(pal.PalDeckID),
        pal.IsTower,
        pal.IsBOSS,
        pal.IsRarePal or False,
        pal.Level or 1,
    )


class RosterIndex:
    def __init__(self, manager) -> None:
        self._manager = manager

    def working_records(self) -> list[PalRecord]:
        """Every Pal standing in a base camp's container, in base-worker order.

        A base worker is not a kind of record, it is a place: an unowned Pal in a
        container some camp owns. The camps say which containers those are and the
        repository's storage index says who is in them, so both halves are index
        hits and neither can drift out of sync with the other.

        With no save open there are no camps to ask, which is a session holding no
        base workers rather than a failure -- the same empty answer `get_players`
        already gives from its own reset repository.
        """
        manager = self._manager
        if manager.camp_data is None:
            return []
        records = [
            record
            for camp in manager.camp_data.get_camps()
            if camp.container_id
            for record in manager.pal_repository.records_for_storage(
                WorldPalAdapter.storage_key(camp.container_id)
            )
            if not record.pal.OwnerPlayerUId
        ]
        return sorted(
            records,
            key=lambda record: (
                alphanumeric_key(record.pal.PalDeckID),
                record.pal.Level or 1,
            ),
        )

    def records_for_roster(self, roster_key: str) -> list[PalRecord]:
        manager = self._manager
        key = str(roster_key)
        if key == "base-workers":
            return self.working_records()
        if key == "global-palbox":
            storage = manager.global_palbox
            if storage is None:
                return []
            return manager.pal_repository.records_for_storage(storage.storage_key)
        if key == "unrostered":
            return self._unrostered_records()
        # A Pal in the Global Palbox can still carry the uid of whoever deposited
        # it; it belongs to that storage's list, not to the depositor's.
        return [
            record
            for record in manager.pal_repository.records_for_owner(key)
            if record.storage_kind != "global_palbox"
        ]

    def _unrostered_records(self) -> list[PalRecord]:
        """Pals no player, base or Global Palbox list claims.

        No owner and no base container, or an owner uid naming a player this save
        does not contain. This is the one roster with no index to ask, which is
        fitting -- it is defined by every other roster failing to match.
        """
        manager = self._manager
        working = {record.record_key for record in self.working_records()}
        return [
            record
            for record in manager.pal_repository.records()
            if record.storage_kind != "global_palbox"
            and manager.get_player(record.pal.OwnerPlayerUId) is None
            and record.record_key not in working
        ]

    def sorted_records_for_roster(self, roster_key: str | UUID) -> list[PalRecord]:
        """A roster in the order the Pal list displays it."""
        return sorted(
            self.records_for_roster(str(roster_key)),
            key=lambda record: paldeck_display_key(record.pal),
        )
