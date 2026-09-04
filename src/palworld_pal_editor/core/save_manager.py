import copy
from pathlib import Path
import threading
import traceback
from typing import Optional
import uuid

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

from palworld_pal_editor.core.basecamp_data import BaseCampData

from palworld_pal_editor.core.container_data import ContainerData
from palworld_pal_editor.core.item_container_data import ItemContainerData
from palworld_pal_editor.core.locker import LockerIndex

from palworld_pal_editor.core.pal_objects import PalObjects, UUID2HexStr, toUUID
from palworld_pal_editor.core.pal_mutations import PalMutationService
from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage import PalStorageSaveFile
from palworld_pal_editor.core.pal_storage_adapters import (
    DpsPalAdapter,
    GpsPalAdapter,
    PalAdapter,
    WorldPalAdapter,
)
from palworld_pal_editor.core.player_repository import PlayerRepository
from palworld_pal_editor.core.rosters import RosterIndex
from palworld_pal_editor.core.storage_directory import StorageDirectory
from palworld_pal_editor.core.save_codec import (
    MAIN_SKIP_PROPERTIES,
    PLAYER_SKIP_PROPERTIES,
)
from palworld_pal_editor.core.save_io import (
    GLOBAL_STORAGE_NAME,
    SaveFailed,
    backup_saves,
    restore_saves,
)
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.core.group_data import GroupData
from palworld_pal_editor.core.guild_lab_data import GuildLabData



class _WorldDataUnreadable(Exception):
    """Level.sav parsed, but something inside it did not. Never leaves `_open`."""


class SaveManager:
    # Although these are class attrs, SaveManager itself is singleton so it should be fine?
    _instance = None
    file_path: Optional[Path]
    _raw_gvas: Optional[bytes]
    _save_type: Optional[int]

    gvas_file: Optional[GvasFile]
    _entities_list: Optional[list[dict]]

    players: PlayerRepository
    pal_repository: PalRepository
    world_adapter: Optional[WorldPalAdapter]
    storage_adapters: dict[str, "PalAdapter"]
    
    container_data: Optional[ContainerData]
    item_container_data: Optional[ItemContainerData]
    group_data: Optional[GroupData]
    camp_data: Optional[BaseCampData]
    guild_lab_data: Optional[GuildLabData]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self.session_lock = threading.RLock()
            self.reset()

    def reset(self) -> None:
        """Drop every piece of state belonging to the currently loaded save.

        open() calls this on entry and again on any failure exit, so a save that
        fails to parse leaves an empty session instead of the half-read wreckage
        of this attempt mixed with the previous save.
        """
        self.file_path = None
        self._raw_gvas = None
        self._save_type = None
        self.gvas_file = None
        self._entities_list = None

        self.players = PlayerRepository()
        self.pal_repository = PalRepository()
        self.world_adapter = None
        # storageKey -> the adapter that reads and writes that place. A plain
        # routing table: it holds no Pals, no rosters and no descriptors.
        self.storage_adapters: dict[str, PalAdapter] = {}

        self.container_data = None
        self.item_container_data = None
        self.group_data = None
        self.camp_data = None
        self.guild_lab_data = None

        self._dps_storages: dict[str, PalStorageSaveFile] = {}
        self._global_palbox: PalStorageSaveFile | None = None

        # What storages this save has and what each one is. Derived, cached, and
        # invalidated by whatever moved a Pal.
        self.storage_directory = StorageDirectory(self)
        # Which Pals each list shows. Derived on every call, never maintained.
        self.rosters = RosterIndex(self)
        # Which Pals Level.sav says are in a DPS. Maintained by the mutations
        # that put one there or take it out.
        self.locker = LockerIndex(self)
        self.load_warnings: list[str] = []

        # Relocate, replicate and update-existing. It reads this manager rather than
        # holding anything of its own, so a reset replaces it along with everything
        # it would have read.
        self.pal_mutations = PalMutationService(self)

    def open(self, file_path: str) -> Optional[GvasFile]:
        with self.session_lock:
            self.reset()
            try:
                gvas_file = self._open(file_path)
            except Exception as e:
                LOGGER.error(f"Error opening {file_path}: {e}")
                LOGGER.debug(traceback.format_exc())
                gvas_file = None

            if gvas_file is None:
                self.reset()
            return gvas_file

    def _read_level_sav(self, level_sav_path: Path) -> bool:
        """Decompress and parse Level.sav into `gvas_file`. False if it will not read."""
        LOGGER.info(f"Opening {level_sav_path}")
        data = level_sav_path.read_bytes()
        try:
            LOGGER.info("Decompressing sav")
            self._raw_gvas, self._save_type = decompress_sav_to_gvas(data)
        except Exception as error:
            LOGGER.error(
                "Caught Exception: palworld_save_tools::palsav::"
                f"decompress_sav_to_gvas: {error}"
            )
            return False

        LOGGER.info("Reading GVAS file")
        self.gvas_file = GvasFile.read(
            self._raw_gvas, PALWORLD_TYPE_HINTS, MAIN_SKIP_PROPERTIES
        )
        PalObjects.TIME = (
            PalObjects.get_BaseType(self.gvas_file.properties.get("Timestamp"))
            or PalObjects.TIME
        )
        return True

    def _read_world_data(self) -> None:
        """Build every reader over the loaded world data.

        Each of these was its own try/except answering None, five times over. The
        answer is the same for all of them -- a save whose world data will not parse
        is a save this cannot open -- so it is said once, and what failed travels in
        the exception instead of in a log line at each site.
        """

        def parse(label: str, build):
            try:
                return build()
            except Exception as error:
                raise _WorldDataUnreadable(f"Error parsing {label}: {error}") from error

        self.group_data = parse("group data", lambda: GroupData(self.gvas_file))
        self.camp_data = parse("base camp data", lambda: BaseCampData(self.gvas_file))
        self.guild_lab_data = parse(
            "guild laboratory data",
            lambda: GuildLabData(
                self.gvas_file,
                DataProvider.get_lab_research_data(),
                DataProvider.get_lab_research_labels(),
            ),
        )
        self.container_data = parse(
            "container data", lambda: ContainerData(self.gvas_file)
        )
        self.item_container_data = parse(
            "item container data", lambda: ItemContainerData(self.gvas_file)
        )
        self._entities_list = parse(
            "pal data",
            lambda: self.gvas_file.properties["worldSaveData"]["value"][
                "CharacterSaveParameterMap"
            ]["value"],
        )

    def _bind_world_adapter(self) -> None:
        """Every world container reads and writes through the one world adapter."""
        self.world_adapter = WorldPalAdapter(self._entities_list, self.container_data)
        for container in self.container_data.get_containers():
            self.storage_adapters[
                WorldPalAdapter.storage_key(container.ID)
            ] = self.world_adapter

    def _open(self, file_path: str) -> Optional[GvasFile]:
        self.file_path = Path(file_path).resolve()
        level_sav_path = self.file_path / "Level.sav"
        if not level_sav_path.exists():
            LOGGER.error(f"Save file does not exist: {level_sav_path}.")
            return None
        if not self._read_level_sav(level_sav_path):
            return None
        try:
            self._read_world_data()
        except _WorldDataUnreadable as failure:
            LOGGER.error(str(failure))
            return None

        self._bind_world_adapter()
        self._load_players()
        self._register_world_records()
        self._load_external_storages()
        self.storage_directory.invalidate()
        LOGGER.info("Done")
        return self.gvas_file

    def save(self, file_path: str) -> bool:
        with self.session_lock:
            return self._save(file_path)

    def _serialize_session(
        self, output_path: Path, global_storage_path: Path
    ) -> tuple[list[tuple[Path, bytes]], list[PalStorageSaveFile]]:
        """Every file this session would write, as bytes, and the storages that owe one.

        Nothing is written here and nothing is mutated: this is the whole of what
        the session knows about producing a save, separated from the backup and
        restore around it. The bytes come from a deepcopy of each live GVAS so a
        successful save leaves the session exactly as it was -- still live, still
        the same objects the open editor is holding.
        """
        outputs: list[tuple[Path, bytes]] = [
            (
                output_path / "Level.sav",
                compress_gvas_to_sav(
                    copy.deepcopy(self.gvas_file).write(MAIN_SKIP_PROPERTIES),
                    self._save_type,
                ),
            )
        ]
        for player in self.players:
            if player.PlayerGVAS is None:
                continue
            player_gvas, player_save_type = player.PlayerGVAS
            outputs.append(
                (
                    output_path / "Players" / f"{UUID2HexStr(player.PlayerUId)}.sav",
                    compress_gvas_to_sav(
                        copy.deepcopy(player_gvas).write(PLAYER_SKIP_PROPERTIES),
                        player_save_type,
                    ),
                )
            )

        dirty_storages = [
            storage for storage in self._dps_storages.values() if storage.dirty
        ]
        if self._global_palbox is not None and self._global_palbox.dirty:
            dirty_storages.append(self._global_palbox)
        for storage in dirty_storages:
            target = (
                global_storage_path
                if storage.kind == "global_palbox"
                else output_path / "Players" / storage.path.name
            )
            outputs.append((target, storage.serialize()))
        return outputs, dirty_storages

    def _save(self, file_path: str) -> bool:
        """Write the session to `file_path`, or raise `SaveFailed` having undone it.

        Nothing is staged and nothing is read back to check itself: producing bytes
        the game can load is `palworld-save-tools`' job, and a file that decompresses
        again proves nothing about the save inside it. What does have to hold is that
        a half-written save never survives, and the backup taken before the first
        write is what holds it.

        The bytes come from a deepcopy of each live GVAS so that a successful save
        leaves the session exactly as it was -- still live, still the same objects the
        open editor is holding -- rather than swapping it for what was serialized.
        """
        if self.gvas_file is None or self._save_type is None:
            raise SaveFailed("No save is loaded")

        output_path = Path(file_path).resolve()
        if not output_path.exists():
            if not output_path.parent.exists():
                raise SaveFailed(f"Parent path does not exist: {output_path.parent}")
            LOGGER.info(f"Creating {output_path}")
            output_path.mkdir(parents=True, exist_ok=True)

        global_storage_path = output_path.parent / GLOBAL_STORAGE_NAME
        try:
            backup_dir = backup_saves(output_path, global_storage_path)
        except Exception as error:
            # Nothing has been written yet, so there is nothing to undo -- but there
            # is also no safety net, and that is reason enough not to start.
            raise SaveFailed(f"Could not back up {output_path}: {error}") from error

        settled: dict[str, dict] = {}
        created: list[Path] = []
        dirty_storages: list[PalStorageSaveFile] = []
        try:
            settled = self._settle_created_records()
            outputs, dirty_storages = self._serialize_session(
                output_path, global_storage_path
            )
            # Files this save is about to bring into existence. Putting a backup back
            # cannot undo those, so undoing them means deleting them.
            created = [target for target, _ in outputs if not target.exists()]
            for target, sav_data in outputs:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(sav_data)
                LOGGER.info(f"Saved {target}")
        except Exception as error:
            LOGGER.error(f"Save failed: {traceback.format_exc()}")
            restored = True
            try:
                restore_saves(backup_dir, output_path, created)
            except Exception:
                restored = False
                LOGGER.critical(
                    f"Could not put {output_path} back the way it was. The save files "
                    f"there are the half-written ones, and {backup_dir} is now the "
                    f"only complete copy: {traceback.format_exc()}"
                )
            # The settlement was folded in for a save that did not happen, so the
            # players go back to what they were and the next attempt settles once.
            self._restore_settled_records(settled)
            raise SaveFailed(
                f"Could not save to {output_path}: {error}",
                backup_path=backup_dir,
                restored=restored,
            ) from error

        for storage in dirty_storages:
            storage.dirty = False
        # Every output file is on disk, so the settlement they contain is durable,
        # the created set may finally be consumed, and every Pal on screen is once
        # again what the save says it is.
        self.pal_repository.clear_created()
        self.pal_repository.clear_modified()
        return True

    def _settle_created_records(self) -> dict[str, dict]:
        """Fold this session's created Pals into their owners' capture records.

        Returns the pre-settlement snapshot of every player it touched. It does not
        clear the created set: the old path cleared its tracker right here, so a save
        that failed afterwards had already applied the capture counts and paldeck
        flags to the in-memory player GVAS while losing the record that it had to,
        and the retry silently under-counted. Consuming the set is `save()`'s job,
        once every output file is written.
        """
        snapshots: dict[str, dict] = {}
        for record in self.pal_repository.created_records():
            owner = (
                self.get_player(record.pal.OwnerPlayerUId)
                if record.pal.OwnerPlayerUId
                else None
            )
            # A created Pal with no owner -- a base worker, or a Global Palbox Pal --
            # has no player records to settle into.
            if owner is None:
                continue
            uid = str(owner.PlayerUId)
            if uid not in snapshots:
                snapshots[uid] = owner.snapshot_capture_records()
            owner.settle_captured_pal(record.pal)
        return snapshots

    def _restore_settled_records(self, snapshots: dict[str, dict]) -> None:
        for uid, snapshot in snapshots.items():
            player = self.get_player(uid)
            if player is not None:
                player.restore_capture_records(snapshot)

    def load_player_sav(self, player_uid: str | UUID) -> GvasFile:
        player_path: Path = self.file_path / "Players" / f"{UUID2HexStr(player_uid)}.sav"
        LOGGER.info(f"Loading Player SAV: {player_path}")
        if not player_path.exists():
            LOGGER.error(f"Player SAV {str(player_path.absolute())} not exist")
            raise Exception(f"Player SAV {str(player_path.absolute())} not exist")
        with player_path.open("rb") as player_file:
            player_data = player_file.read()
        raw_gvas, compression_times = decompress_sav_to_gvas(player_data)
        player_gvas_file = GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, PLAYER_SKIP_PROPERTIES)
        return player_gvas_file, compression_times

    def _load_players(self) -> None:
        """Create every PlayerEntity from the World save's character array.

        Runs before any Pal is registered, so a Pal's owner either exists by the time
        its record is built or never will.
        """
        for native_record in self._entities_list:
            if not WorldPalAdapter.is_player(native_record):
                continue
            try:
                parameter = WorldPalAdapter.save_parameter(native_record)["value"]
                uid_str = str(
                    PalObjects.get_BaseType(native_record["key"].get("PlayerUId"))
                )
                nickname = str(PalObjects.get_BaseType(parameter.get("NickName")))
                LOGGER.info(f"Players found: {nickname} - {uid_str}")
                if uid_str in self.players:
                    LOGGER.error(
                        f"Duplicated player found: \n\t{self.players.get(uid_str)}, "
                        "skipping..."
                    )
                    continue

                group_id = self.group_data.get_player_group_id(uid_str)
                if group_id is None:
                    LOGGER.warning(f"Player {uid_str} has no guild id")
                    continue

                player_gvas_file, player_compress_times = self.load_player_sav(uid_str)
                player_entity = PlayerEntity(
                    group_id,
                    native_record,
                    player_gvas_file,
                    player_compress_times,
                )
                self.players.register(player_entity)
                LOGGER.info(f"Player Object Created: {player_entity}")
            except Exception as e:
                LOGGER.error(f"Error occured while init'in object: {e}, skipping")
                continue

    @property
    def has_global_palbox(self) -> bool:
        return self._global_palbox is not None

    @property
    def dps_storages(self) -> dict[str, PalStorageSaveFile]:
        """Every loaded Dimensional Pal Storage, by storage key."""
        return self._dps_storages

    @property
    def global_palbox(self) -> Optional[PalStorageSaveFile]:
        return self._global_palbox

    def _unregister_record(self, record: PalRecord) -> None:
        self.pal_repository.unregister(record)

    def _register_external_record(
        self, record: PalRecord, *, created: bool = False
    ) -> None:
        owner = self.get_player(record.pal.OwnerPlayerUId)
        if owner is not None:
            record.group_id = owner.group_id
        self.pal_repository.register(record, created=created)

    def _register_world_records(self) -> None:
        """Register every World Pal and file it under the roster it belongs to.

        The Pal's own record decides where it belongs: an owner that exists, a base
        container it really occupies, or neither.
        """
        base_container_ids = {
            str(camp.container_id)
            for camp in self.camp_data.get_camps()
            if camp.container_id
        }
        for record in self.world_adapter.records():
            pal = record.pal
            owner = self.get_player(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None
            if owner is not None:
                self.pal_repository.register(record)
                LOGGER.info(f"Found pal: {pal}")
                continue

            self.pal_repository.register(record)
            if pal.OwnerPlayerUId:
                LOGGER.warning(
                    f"Found pal owned by non-existing user {pal.OwnerPlayerUId}: {pal}"
                )

        for player in self.players:
            LOGGER.newline()
            LOGGER.info(f"{player}")
            for record in self.rosters.sorted_records_for_roster(player.PlayerUId):
                LOGGER.info(f"\t{record.pal}")

        LOGGER.newline()
        LOGGER.info("Pals possibly working at the base: ")
        for pal in self.get_working_pals():
            LOGGER.info(f"\t{pal}")

        self._log_location_anomalies()

    def _log_location_anomalies(self) -> None:
        """One WARNING per Pal whose recorded container slot does not hold it.

        A container location anomaly gets a load log line and nothing else
        -- no anomaly set, no query index, no UI field, no second roster. Every value
        here is read back out of the save at the moment of logging, so the anomaly
        outlives this call only as text.
        """
        for record in self.pal_repository.records():
            if record.storage_kind != "world" or record.storage_key is not None:
                continue
            pal = record.pal
            container = self.container_data.get_container(pal.ContainerId)
            slot = (
                None
                if container is None
                else next(
                    (
                        slot
                        for slot in container.slots
                        if slot.SlotIndex == pal.SlotIndex
                    ),
                    None,
                )
            )
            LOGGER.warning(
                "Container location anomaly: "
                f"record_key={record.record_key} InstanceId={pal.InstanceId} "
                f"ContainerId={pal.ContainerId} SlotIndex={pal.SlotIndex} "
                f"container_exists={container is not None} "
                f"slot_exists={slot is not None} "
                f"slot_instance_id={slot.instance_id if slot is not None else None}"
            )

    def _load_external_storages(self) -> None:
        players_path = self.file_path / "Players"
        for dps_path in sorted(players_path.glob("*_dps.sav")):
            owner_hex = dps_path.stem.removesuffix("_dps")
            try:
                owner_uid = toUUID(str(uuid.UUID(owner_hex)))
                storage = PalStorageSaveFile.open(dps_path, "dps", owner_uid)
                self._dps_storages[storage.storage_key] = storage
                adapter = DpsPalAdapter(storage)
                self.storage_adapters[storage.storage_key] = adapter
                LOGGER.info(
                    f"Loaded DPS: path={dps_path} owner={owner_uid} "
                    f"occupied={storage.occupied}/{storage.capacity}"
                )
                for record in adapter.records():
                    self._register_external_record(record)
            except Exception as error:
                warning = f"Unable to load DPS {dps_path}: {error}"
                self.load_warnings.append(warning)
                LOGGER.warning(warning)

        gps_path = self.file_path.parent / GLOBAL_STORAGE_NAME
        if not gps_path.exists():
            return
        try:
            self._global_palbox = PalStorageSaveFile.open(
                gps_path, "global_palbox"
            )
            adapter = GpsPalAdapter(self._global_palbox)
            self.storage_adapters[self._global_palbox.storage_key] = adapter
            LOGGER.info(
                f"Loaded Global Palbox: path={gps_path} "
                f"occupied={self._global_palbox.occupied}/"
                f"{self._global_palbox.capacity}"
            )
            for record in adapter.records():
                self.pal_repository.register(record)
        except Exception as error:
            warning = f"Unable to load Global Palbox {gps_path}: {error}"
            self.load_warnings.append(warning)
            LOGGER.warning(warning)
            if self._global_palbox is not None:
                self.storage_adapters.pop(self._global_palbox.storage_key, None)
            self._global_palbox = None

    def get_record(self, record_key: str) -> Optional[PalRecord]:
        return self.pal_repository.get(record_key)

    def records_by_instance(
        self, instance_id: UUID | str, domain: str = "all"
    ) -> list[PalRecord]:
        records = self.pal_repository.records_by_instance(instance_id)
        if domain == "all":
            return records
        if domain == "world":
            return [record for record in records if record.storage_kind == "world"]
        if domain == "gps":
            return [
                record
                for record in records
                if record.storage_kind == "global_palbox"
            ]
        if domain == "dps":
            return [record for record in records if record.storage_kind == "dps"]
        raise ValueError(f"Unknown Pal record domain: {domain}")






    def get_players(self) -> list[PlayerEntity]:
        return self.players.all()

    def get_lab_research(self) -> dict:
        if self.guild_lab_data is None:
            raise ValueError("Guild laboratory data is not loaded")
        return self.guild_lab_data.snapshot(self.group_data, self.camp_data)

    def complete_lab_research(
        self,
        guild_id: str,
        *,
        research_id: str | None = None,
        category: str | None = None,
        all_research: bool = False,
    ) -> int:
        if self.guild_lab_data is None:
            raise ValueError("Guild laboratory data is not loaded")
        return self.guild_lab_data.complete(
            guild_id,
            research_id=research_id,
            category=category,
            all_research=all_research,
        )
    
    def get_player(self, guid: UUID | str) -> Optional[PlayerEntity]:
        return self.players.get(guid)

    def get_players_by_name(self, name: str) -> list[PlayerEntity]:
        return self.players.by_name(name)
    
    def get_pal(self, guid: UUID | str) -> Optional[PalEntity]:
        records = self.records_by_instance(guid)
        if not records:
            LOGGER.warning(f"Can't find pal {guid}")
            return None
        # A World copy wins over a DPS/GPS one sharing the Instance ID, which is the
        # order the old baseworker-then-dangling-then-palbox scan happened to produce.
        world = [record for record in records if record.storage_kind == "world"]
        return (world[0] if world else records[0]).pal

    def get_working_pals(self) -> list[PalEntity]:
        return [record.pal for record in self.rosters.working_records()]














    
    
