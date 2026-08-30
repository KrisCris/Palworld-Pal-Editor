import copy
from datetime import datetime
from pathlib import Path
import re
import shutil
import threading
import traceback
from typing import Literal, Optional
import uuid

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

from palworld_pal_editor.core.basecamp_data import BaseCampData

from palworld_pal_editor.core.container_data import ContainerData
from palworld_pal_editor.core.item_container_data import ItemContainerData

from palworld_pal_editor.core.pal_objects import PalObjects, UUID2HexStr, toUUID
from palworld_pal_editor.core.pal_operations import (
    PalIdentityConflict,
    PalOperationService,
    prepare_global_parameter,
    restore_local_parameter_envelope,
    set_owner,
)
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
from palworld_pal_editor.core.save_codec import (
    MAIN_SKIP_PROPERTIES,
    PAL_STORAGE_CUSTOM_PROPERTIES,
    PLAYER_SKIP_PROPERTIES,
)
from palworld_pal_editor.utils import LOGGER, DataProvider, alphanumeric_key
from palworld_pal_editor.core.group_data import GroupData
from palworld_pal_editor.core.guild_lab_data import GuildLabData

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

        self._container_registry_cache = None
        self.load_warnings: list[str] = []

        # Relocate, replicate and update-existing. It reads this manager rather than
        # holding anything of its own, so a reset replaces it along with everything
        # it would have read (spec §4.5).
        self.pal_operations = PalOperationService(self)

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

    def _open(self, file_path: str) -> Optional[GvasFile]:
        self.file_path = Path(file_path).resolve()

        level_sav_path = self.file_path / "Level.sav"

        if not level_sav_path.exists():
            LOGGER.error(f"Save file does not exist: {level_sav_path}.")
            return None

        LOGGER.info(f"Opening {level_sav_path}")
        with level_sav_path.open("rb") as file:
            data = file.read()

            try:
                LOGGER.info("Decompressing sav")
                self._raw_gvas, self._save_type = decompress_sav_to_gvas(data)
            except Exception as e:
                LOGGER.error(f"Caught Exception: palworld_save_tools::palsav::decompress_sav_to_gvas: {e}")
                return None

            LOGGER.info("Reading GVAS file")
            self.gvas_file = GvasFile.read(
                self._raw_gvas, PALWORLD_TYPE_HINTS, MAIN_SKIP_PROPERTIES
            )

            PalObjects.TIME = PalObjects.get_BaseType(self.gvas_file.properties.get("Timestamp")) or PalObjects.TIME

            try:
                self.group_data = GroupData(self.gvas_file)
            except Exception as e:
                LOGGER.error(f"Error parsing group data: {e}")
                return None
            
            try:
                self.camp_data = BaseCampData(self.gvas_file)
            except Exception as e:
                LOGGER.error(f"Error parsing base camp data: {e}")
                return None

            try:
                self.guild_lab_data = GuildLabData(
                    self.gvas_file,
                    DataProvider.get_lab_research_data(),
                    DataProvider.get_lab_research_labels(),
                )
            except Exception as e:
                LOGGER.error(f"Error parsing guild laboratory data: {e}")
                return None
            
            try:
                self.container_data = ContainerData(self.gvas_file)
            except Exception as e:
                LOGGER.error(f"Error parsing container data: {e}")
                return None

            try:
                self.item_container_data = ItemContainerData(self.gvas_file)
            except Exception as e:
                LOGGER.error(f"Error parsing item container data: {e}")
                return None

            try:
                self._entities_list = self.gvas_file.properties["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]
            except Exception as e:
                LOGGER.error(f"Unable to retrieve pal data: {e}")
                return None

            self.world_adapter = WorldPalAdapter(
                self._entities_list, self.container_data
            )
            for container in self.container_data.get_containers():
                self.storage_adapters[
                    WorldPalAdapter.storage_key(container.ID)
                ] = self.world_adapter

            self._load_players()
            self._register_world_records()
            self._load_external_storages()
            self._container_registry_cache = None

            LOGGER.info("Done")
        return self.gvas_file

    def save(self, file_path: str) -> bool:
        with self.session_lock:
            return self._save(file_path)

    def _save(self, file_path: str) -> bool:
        if self.gvas_file is None:
            LOGGER.error("No gvas_file stored in save manager, aborting")
            return False
        if self._save_type is None:
            LOGGER.warning("_save_type is None, aborting")
            return False

        output_path = Path(file_path).resolve() 

        if not output_path.exists():
            LOGGER.warning(f"Path does not exist: {output_path}")
            if output_path.parent.exists():
                output_path.mkdir(parents=True, exist_ok=True)
                LOGGER.debug(f"Path {output_path} created")
            else:
                LOGGER.error(f"Parent path {output_path.parent} does not exist, skipping")
                return False
            
        if output_path.exists():
            BK_FOLDER_NAME = "Palworld-Pal-Editor-Backup"
            backup_dir = output_path / BK_FOLDER_NAME / f"{datetime.now().strftime(r'%Y-%m-%d_%H-%M-%S')}"
            try:
                if output_path.exists():
                    LOGGER.info(f"Saving backup of {output_path} to {backup_dir}")
                    shutil.copytree(self.file_path, backup_dir, 
                                    ignore=lambda dir, files: [f for f in files if not f == "Players" and not f.endswith('.sav')])
                    global_storage_path = output_path.parent / "GlobalPalStorage.sav"
                    if (
                        self._global_palbox is not None
                        and global_storage_path.exists()
                    ):
                        global_storage_backup = backup_dir / global_storage_path.name
                        LOGGER.info(
                            "Saving Global Pal Storage backup: "
                            f"source={global_storage_path} "
                            f"destination={global_storage_backup}"
                        )
                        shutil.copy2(global_storage_path, global_storage_backup)
                else:
                    LOGGER.info(f"No existing directory to backup: {output_path}")
            except Exception as e:
                LOGGER.error(f"Error backing up directory: {e}")
                return False

        outputs: list[tuple[Path, bytes, dict]] = []
        level_data = compress_gvas_to_sav(
            copy.deepcopy(self.gvas_file).write(MAIN_SKIP_PROPERTIES),
            self._save_type,
        )
        outputs.append((output_path / "Level.sav", level_data, MAIN_SKIP_PROPERTIES))
        settled = self._settle_created_records()
        for player in self.players:
            if player.PlayerGVAS is None:
                continue
            player_gvas, player_save_type = player.PlayerGVAS
            player_data = compress_gvas_to_sav(
                copy.deepcopy(player_gvas).write(PLAYER_SKIP_PROPERTIES),
                player_save_type,
            )
            outputs.append(
                (
                    output_path
                    / "Players"
                    / f"{UUID2HexStr(player.PlayerUId)}.sav",
                    player_data,
                    PLAYER_SKIP_PROPERTIES,
                )
            )
        dirty_storages = [
            storage for storage in self._dps_storages.values() if storage.dirty
        ]
        if self._global_palbox is not None and self._global_palbox.dirty:
            dirty_storages.append(self._global_palbox)
        for storage in dirty_storages:
            target = (
                output_path.parent / "GlobalPalStorage.sav"
                if storage.kind == "global_palbox"
                else output_path / "Players" / storage.path.name
            )
            outputs.append(
                (target, storage.serialize(), PAL_STORAGE_CUSTOM_PROPERTIES)
            )

        staged: list[tuple[Path, Path]] = []
        backups: dict[Path, Path | None] = {}
        replaced: list[Path] = []
        transaction_id = uuid.uuid4().hex
        try:
            for target, sav_data, custom_properties in outputs:
                target.parent.mkdir(parents=True, exist_ok=True)
                staged.append(
                    (target, self._staged_output(target, sav_data, custom_properties))
                )
            for target, _ in staged:
                if target.exists():
                    backup = target.with_name(
                        f".{target.name}.{transaction_id}.bak"
                    )
                    shutil.copy2(target, backup)
                    backups[target] = backup
                else:
                    backups[target] = None
            for target, temp in staged:
                self._replace_staged_output(temp, target)
                replaced.append(target)
                LOGGER.info(f"Saved verified output: file_path={target}")
        except Exception:
            LOGGER.error(
                f"Save transaction failed; restoring outputs: {traceback.format_exc()}"
            )
            for target in reversed(replaced):
                backup = backups.get(target)
                try:
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        shutil.copy2(backup, target)
                    LOGGER.info(f"Restored output: file_path={target}")
                except Exception:
                    LOGGER.critical(
                        f"Failed restoring output {target}: {traceback.format_exc()}"
                    )
            self._restore_settled_records(settled)
            return False
        finally:
            for _, temp in staged:
                temp.unlink(missing_ok=True)
            for backup in backups.values():
                if backup is not None:
                    backup.unlink(missing_ok=True)
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

    @staticmethod
    def _staged_output(
        path: Path,
        sav_data: bytes,
        custom_properties: dict,
    ) -> Path:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_bytes(sav_data)
            raw_gvas, _ = decompress_sav_to_gvas(temp.read_bytes())
            GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, custom_properties)
            return temp
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    @staticmethod
    def _replace_staged_output(temp: Path, target: Path) -> None:
        temp.replace(target)
    
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
    
    
    def save_player_sav(self, player_entity: PlayerEntity, save_path: Optional[Path] = None) -> bool:
        if player_entity.PlayerGVAS is None:
            return False

        gvas_file, compression_times = player_entity.PlayerGVAS
        output_path = (save_path or self.file_path) / "Players"
        if not output_path.exists() and output_path.parent.exists():
            LOGGER.warning(f"Player path does not exist: {output_path}")
            output_path.mkdir(parents=True, exist_ok=True)
            LOGGER.info(f"Player path {output_path} created")

        player_path: Path = output_path / f"{UUID2HexStr(player_entity.PlayerUId)}.sav"

        LOGGER.info(f"Compressing Player {player_entity} GVAS file")
        player_gvas_file = copy.deepcopy(gvas_file)
        sav_data = compress_gvas_to_sav(
            player_gvas_file.write(PLAYER_SKIP_PROPERTIES), compression_times
        )

        LOGGER.info(f"Saving to {player_path}")
        with player_path.open("wb") as file:
            file.write(sav_data)
        LOGGER.info(f"Saved to {player_path}")
        return True
    
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
        """Register every World Pal and file it under the roster the old UI asks for.

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
            for record in self.sorted_records_for_roster(player.PlayerUId):
                LOGGER.info(f"\t{record.pal}")

        LOGGER.newline()
        LOGGER.info("Pals possibly working at the base: ")
        for pal in self.get_working_pals():
            LOGGER.info(f"\t{pal}")

        self._log_location_anomalies()

    def _log_location_anomalies(self) -> None:
        """One WARNING per Pal whose recorded container slot does not hold it.

        Spec §9: a container location anomaly gets a load log line and nothing else
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

        gps_path = self.file_path.parent / "GlobalPalStorage.sav"
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

    def _unused_instance_id(self, *claimed) -> UUID:
        """A Pal id nothing in this save is already using.

        `claimed` are the native structures the caller is about to write into -- a
        container, a guild. Those can hold a handle for an id the repository has no
        record for, and a Pal given that id would be the second thing answering to
        it in the save file.
        """
        while True:
            instance_id = toUUID(str(uuid.uuid4()))
            if self.records_by_instance(instance_id):
                continue
            if any(structure.has_pal(instance_id) for structure in claimed):
                continue
            return instance_id

    def working_records(self) -> list[PalRecord]:
        """Every Pal standing in a base camp's container, in base-worker order.

        A base worker is not a kind of record, it is a place: an unowned Pal in a
        container some camp owns. The camps say which containers those are and the
        repository's storage index says who is in them, so both halves are index
        hits and neither can drift out of sync with the other.
        """
        records = [
            record
            for camp in self.camp_data.get_camps()
            if camp.container_id
            for record in self.pal_repository.records_for_storage(
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
        """The Pals one of the old UI's lists shows, derived on every call.

        Until F3b this was a hand-maintained list of record keys per roster, and
        every create, move and transfer had to remember to re-file it -- forgetting
        was silent and left the list pointing at the previous owner. Nothing is
        stored now, so nothing can go stale.
        """
        key = str(roster_key)
        if key == "PAL_BASE_WORKER_BTN":
            return self.working_records()
        if key == "PAL_GLOBAL_STORAGE_BTN":
            if self._global_palbox is None:
                return []
            return self.pal_repository.records_for_storage(
                self._global_palbox.storage_key
            )
        if key == "PAL_OTHER_PAL_BTN":
            return self._unrostered_records()
        # A Pal in the Global Palbox can still carry the uid of whoever deposited
        # it; it belongs to that storage's list, not to the depositor's.
        return [
            record
            for record in self.pal_repository.records_for_owner(key)
            if record.storage_kind != "global_palbox"
        ]

    def _unrostered_records(self) -> list[PalRecord]:
        """Pals no player, base or Global Palbox list claims.

        No owner and no base container, or an owner uid naming a player this save
        does not contain. This is the one roster with no index to ask, which is
        fitting -- it is defined by every other roster failing to match.
        """
        working = {record.record_key for record in self.working_records()}
        return [
            record
            for record in self.pal_repository.records()
            if record.storage_kind != "global_palbox"
            and self.get_player(record.pal.OwnerPlayerUId) is None
            and record.record_key not in working
        ]

    def sorted_records_for_roster(self, roster_key: str | UUID) -> list[PalRecord]:
        """A roster in the order the Pal list displays it."""
        return sorted(
            self.records_for_roster(str(roster_key)),
            key=lambda record: paldeck_display_key(record.pal),
        )

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
        return [record.pal for record in self.working_records()]

    def _container_descriptor_map(self) -> dict[str, dict]:
        cached = self._container_registry_cache
        if cached is not None:
            return cached
        descriptors = {}

        def add_descriptor(container_id, **values):
            container = self.container_data.get_container(container_id)
            if container is None:
                return
            descriptors[str(container.ID)] = {
                "ContainerId": str(container.ID),
                "StorageKey": f"world-container:{container.ID}",
                "StorageKind": "world",
                "ContainerKind": values["kind"],
                "ContainerLabel": values["label"],
                "OwnerPlayerUId": values.get("owner_player_uid"),
                "StorageOwnerPlayerUid": values.get("owner_player_uid"),
                "OwnerName": values.get("owner_name"),
                "BaseId": values.get("base_id"),
                "BaseName": values.get("base_name"),
                "BaseOrdinal": values.get("base_ordinal"),
                "GroupId": values.get("group_id"),
                "Size": container.size,
                "Capacity": container.size,
                "Occupied": len(container.slots),
                "Classification": values["classification"],
                "MovableInto": values["movable_into"],
                "CloneableInto": False,
                "Shared": values.get("shared", False),
                "Anomaly": values.get("anomaly"),
            }

        for player in self.get_players():
            owner_id = str(player.PlayerUId)
            group_id = str(player.group_id) if player.group_id else None
            add_descriptor(
                player.OtomoCharacterContainerId,
                kind="party",
                label=f"{player.NickName} · Party",
                owner_player_uid=owner_id,
                owner_name=player.NickName,
                group_id=group_id,
                classification="exact",
                movable_into=True,
            )
            add_descriptor(
                player.PalStorageContainerId,
                kind="storage",
                label=f"{player.NickName} · Palbox",
                owner_player_uid=owner_id,
                owner_name=player.NickName,
                group_id=group_id,
                classification="exact",
                movable_into=True,
            )

        for base_ordinal, camp in enumerate(self.camp_data.get_camps(), start=1):
            template_match = re.fullmatch(
                r"新規生成拠点テンプレート名(\d+)\(仮\)", camp.name or ""
            )
            display_ordinal = base_ordinal if template_match else None
            add_descriptor(
                camp.container_id,
                kind="base",
                label=(
                    f"Base {display_ordinal}"
                    if display_ordinal is not None
                    else camp.name or f"Base {str(camp.id)[:8]}"
                ),
                base_id=str(camp.id),
                base_name=camp.name,
                base_ordinal=display_ordinal,
                group_id=str(camp.owner_group_id),
                classification="exact",
                movable_into=True,
            )

        for container in self.container_data.get_containers():
            container_id = str(container.ID)
            if container_id in descriptors:
                continue

            if container.size == 40:
                add_descriptor(
                    container.ID,
                    kind="special",
                    label="Viewing Cage",
                    classification="inferred",
                    movable_into=True,
                    shared=True,
                )
                continue

            owners = []
            unresolved = False
            for slot in container.slots:
                pal = self.get_pal(slot.instance_id)
                if pal is None or pal.OwnerPlayerUId is None:
                    unresolved = True
                    continue
                owners.append(str(pal.OwnerPlayerUId))

            unique_owners = set(owners)
            if (
                container.slots
                and not unresolved
                and len(owners) == len(container.slots)
                and len(unique_owners) == 1
            ):
                owner_id = owners[0]
                owner = self.get_player(owner_id)
                if owner is not None:
                    kind_label = f"Special container ({container.size} slots)"
                    add_descriptor(
                        container.ID,
                        kind="special",
                        label=f"{owner.NickName} · {kind_label}",
                        owner_player_uid=owner_id,
                        owner_name=owner.NickName,
                        group_id=str(owner.group_id),
                        classification="inferred",
                        movable_into=True,
                    )
                    continue

            anomaly = "mixed_owner" if len(unique_owners) > 1 else None
            add_descriptor(
                container.ID,
                kind="unknown",
                label=f"Unknown container ({container.size} slots)",
                classification="unknown",
                movable_into=False,
                anomaly=anomaly,
            )

        dps_name = DataProvider.get_tech_name("DimensionPalStorage") or (
            "Dimensional Pal Storage"
        )
        for storage in self._dps_storages.values():
            owner = self.get_player(storage.owner_uid)
            owner_name = owner.NickName if owner else storage.owner_uid
            descriptors[storage.storage_key] = {
                "ContainerId": None,
                "StorageKey": storage.storage_key,
                "StorageKind": "dps",
                "ContainerKind": "dps",
                "ContainerLabel": f"{owner_name} · {dps_name}",
                "OwnerPlayerUId": storage.owner_uid,
                "StorageOwnerPlayerUid": storage.owner_uid,
                "OwnerName": owner_name,
                "BaseId": None,
                "BaseName": None,
                "BaseOrdinal": None,
                "GroupId": str(owner.group_id) if owner else None,
                "Size": storage.capacity,
                "Capacity": storage.capacity,
                "Occupied": storage.occupied,
                "Classification": "exact" if owner else "unknown_owner",
                "MovableInto": True,
                "CloneableInto": False,
                "Shared": True,
                "Anomaly": None if owner else "unknown_storage_owner",
            }

        if self._global_palbox is not None:
            storage = self._global_palbox
            descriptors[storage.storage_key] = {
                "ContainerId": None,
                "StorageKey": storage.storage_key,
                "StorageKind": "global_palbox",
                "ContainerKind": "global_palbox",
                "ContainerLabel": (
                    DataProvider.get_tech_name("GlobalPalStorage")
                    or "Global Palbox"
                ),
                "OwnerPlayerUId": None,
                "StorageOwnerPlayerUid": None,
                "OwnerName": None,
                "BaseId": None,
                "BaseName": None,
                "BaseOrdinal": None,
                "GroupId": None,
                "Size": storage.capacity,
                "Capacity": storage.capacity,
                "Occupied": storage.occupied,
                "Classification": "exact",
                "MovableInto": False,
                "CloneableInto": True,
                "Shared": True,
                "Anomaly": None,
            }

        self._container_registry_cache = descriptors
        return descriptors

    def get_container_registry(self) -> list[dict]:
        order = {
            "global_palbox": -1,
            "party": 0,
            "storage": 1,
            "dps": 2,
            "special": 3,
            "base": 4,
            "unknown": 5,
        }
        return sorted(
            self._container_descriptor_map().values(),
            key=lambda item: (
                item.get("GroupId") or "",
                order.get(item["ContainerKind"], 99),
                item["ContainerLabel"],
                item["ContainerId"],
            ),
        )

    def invalidate_storage_descriptors(self) -> None:
        """Forget the cached descriptors after a Pal changed how full something is."""
        self._container_registry_cache = None

    def get_storage_descriptor(self, storage_key: str) -> Optional[dict]:
        return next(
            (
                descriptor
                for descriptor in self._container_descriptor_map().values()
                if descriptor["StorageKey"] == str(storage_key)
                or descriptor.get("ContainerId") == str(storage_key)
            ),
            None,
        )

    def resolve_record_location(self, record: PalRecord | str) -> dict:
        """Where a record sits, and what that place is called.

        Since F4 there is only one location: the one the Pal records for itself,
        already validated at load. A World record that failed that check has no
        storage key and no container to name.
        """
        record_ref = record if isinstance(record, PalRecord) else self.get_record(record)
        if record_ref is None:
            raise ValueError("Pal record not found")
        pal = record_ref.pal
        is_world = record_ref.storage_kind == "world"
        located = record_ref.storage_key is not None
        container_id = (
            str(pal.ContainerId) if is_world and located and pal.ContainerId else None
        )
        descriptor = (
            (self._container_descriptor_map().get(container_id) if located else None)
            if is_world
            else self.get_storage_descriptor(record_ref.storage_key)
        )
        return {
            # The container and slot the record actually occupies. A World record that
            # failed its load-time slot check occupies neither, and says so.
            "ContainerId": container_id,
            "SlotIndex": record_ref.slot_index,
            "ContainerKind": (
                descriptor["ContainerKind"]
                if descriptor
                else (None if is_world else record_ref.storage_kind)
            ),
            "ContainerLabel": descriptor["ContainerLabel"] if descriptor else None,
            "StorageKey": record_ref.storage_key,
            "StorageKind": record_ref.storage_kind,
        }

    def locker_entries(self) -> list[dict]:
        world_data = self.gvas_file.properties["worldSaveData"]["value"]
        locker = world_data.get("InLockerCharacterInstanceIDArray")
        if locker is None:
            locker = {
                "set_type": "StructProperty",
                "id": None,
                "struct_type": "StructProperty",
                "type": "SetProperty",
                "value": [],
            }
            world_data["InLockerCharacterInstanceIDArray"] = locker
        return locker["value"]

    @staticmethod
    def _locker_instance_id(entry: dict) -> Optional[UUID]:
        return PalObjects.get_BaseType(entry.get("InstanceId"))

    def add_locker_id(self, instance_id: UUID | str) -> None:
        instance_id = toUUID(str(instance_id))
        if any(
            self._locker_instance_id(entry) == instance_id
            for entry in self.locker_entries()
        ):
            return
        self.locker_entries().append(
            {
                "PlayerUId": PalObjects.Guid(PalObjects.EMPTY_UUID),
                "InstanceId": PalObjects.Guid(instance_id),
                "DebugName": PalObjects.StrProperty(""),
            }
        )

    def remove_locker_id(self, instance_id: UUID | str) -> None:
        instance_id = toUUID(str(instance_id))
        entries = self.locker_entries()
        entries[:] = [
            entry
            for entry in entries
            if self._locker_instance_id(entry) != instance_id
        ]

    def _snapshot_external_mutation(
        self,
        external_slots: list[tuple[PalStorageSaveFile, int]],
        containers: list,
    ) -> dict:
        unique_storages = {storage.storage_key: storage for storage, _ in external_slots}
        unique_containers = {str(container.ID): container for container in containers}
        return {
            "external_slots": [
                (storage, index, copy.deepcopy(storage.entries[index]))
                for storage, index in external_slots
            ],
            "storage_dirty": {
                key: storage.dirty for key, storage in unique_storages.items()
            },
            "containers": [
                (container, container.snapshot_slots())
                for container in unique_containers.values()
            ],
            "entities": list(self._entities_list),
            "created": self.pal_repository.snapshot_created(),
            "groups": [
                (group, copy.deepcopy(group.individual_character_handle_ids))
                for group in self.group_data.get_groups()
            ],
            "locker": copy.deepcopy(self.locker_entries()),
            "records": self.pal_repository.snapshot_records(),
            "registry": self._container_registry_cache,
        }

    def _restore_external_mutation(self, snapshot: dict) -> None:
        for storage, index, entry_snapshot in snapshot["external_slots"]:
            entry = storage.entries[index]
            entry.clear()
            entry.update(copy.deepcopy(entry_snapshot))
        for storage, _ in {
            (storage, storage.storage_key)
            for storage, _, _ in snapshot["external_slots"]
        }:
            storage.dirty = snapshot["storage_dirty"][storage.storage_key]
        for container, slot_snapshot in snapshot["containers"]:
            container.restore_slots(slot_snapshot)
        self._entities_list[:] = snapshot["entities"]
        for group, handles in snapshot["groups"]:
            if handles is None:
                group._group_param.pop("individual_character_handle_ids", None)
                group.instance_map = {}
            else:
                group._group_param["individual_character_handle_ids"] = handles
                group.instance_map = {
                    str(handle["instance_id"]): handle for handle in handles
                }
        self.locker_entries()[:] = snapshot["locker"]
        self.pal_repository.replace_records(snapshot["records"])
        self.pal_repository.restore_created(snapshot["created"])
        self._container_registry_cache = snapshot["registry"]

    def _make_world_pal(
        self,
        source: PalRecord,
        descriptor: dict,
        container,
        slot_index: int,
    ) -> tuple[dict, PalEntity, object]:
        source_owner = self.get_player(source.pal.OwnerPlayerUId)
        target_kind = descriptor["ContainerKind"]
        target_owner = self.get_player(descriptor.get("OwnerPlayerUId"))
        if target_kind == "base":
            owner = None
            group_id = descriptor["GroupId"]
        elif descriptor.get("Shared"):
            owner = source_owner
            group_id = source_owner.group_id if source_owner else source.group_id
        else:
            owner = target_owner
            group_id = descriptor["GroupId"]
        group = self.group_data.get_group(group_id)
        if group is None:
            raise ValueError("Target guild is unavailable.")

        pal_obj = PalObjects.PalSaveParameter(
            source.pal.InstanceId,
            source.pal.OwnerPlayerUId or PalObjects.EMPTY_UUID,
            container.ID,
            slot_index,
            group_id,
        )
        pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"] = (
            copy.deepcopy(source.pal.save_parameter)
        )
        pal = WorldPalAdapter.entity(pal_obj)
        pal.InstanceId = source.pal.InstanceId
        pal.PlayerUId = PalObjects.EMPTY_UUID
        pal.SlotId = (container.ID, slot_index)
        if owner is None:
            set_owner(pal, None)
        else:
            set_owner(pal, owner.PlayerUId)
        return pal_obj, pal, group

    def _validate_world_target(self, source: PalRecord, descriptor: dict) -> None:
        source_owner = self.get_player(source.pal.OwnerPlayerUId)
        source_group_id = source_owner.group_id if source_owner else source.group_id
        if descriptor.get("Shared"):
            if source.pal.OwnerPlayerUId is None:
                raise ValueError("A shared container requires a Pal with an owner.")
            return
        if str(source_group_id) != str(descriptor.get("GroupId")):
            raise ValueError("Cross-guild Pal movement is not supported.")

    def normalize_external_record(self, record: PalRecord) -> None:
        if record.storage_kind == "global_palbox":
            save_parameter = prepare_global_parameter(
                record.pal.save_parameter, preserve_provenance=True
            )
            record.pal.pal_param.clear()
            record.pal.pal_param.update(save_parameter["value"])
            self._global_palbox.dirty = True
        elif record.storage_kind == "dps":
            self.add_locker_id(record.pal.InstanceId)
            storage = self._dps_storages.get(record.storage_key)
            if storage is not None:
                storage.dirty = True

    def _global_collision_candidates(self, source: PalRecord) -> list[PalRecord]:
        records = self.records_by_instance(source.pal.InstanceId)
        if source.storage_kind == "global_palbox":
            return [
                record
                for record in records
                if record.storage_kind in {"world", "dps"}
            ]
        return [
            record
            for record in records
            if record.storage_kind == "global_palbox"
        ]

    def _transfer_global(
        self,
        source: PalRecord,
        descriptor: dict,
        action: str,
        expected_target_record_key: str | None,
    ) -> dict:
        is_import = source.storage_kind == "global_palbox"
        if is_import:
            if not (
                descriptor["StorageKind"] == "world"
                and descriptor["ContainerKind"] in {"party", "storage"}
                and descriptor.get("OwnerPlayerUId")
            ):
                raise ValueError(
                    "Global Palbox imports must target a player Party or Palbox."
                )
        elif descriptor["StorageKind"] != "global_palbox":
            raise ValueError("Global Palbox exports must target Global Palbox.")

        candidates = self._global_collision_candidates(source)
        if action == "clone" and candidates:
            raise PalIdentityConflict(candidates)
        if action == "update":
            if len(candidates) != 1:
                if candidates:
                    raise PalIdentityConflict(candidates)
                raise ValueError("No matching destination identity exists.")
            destination = candidates[0]
            if (
                destination.record_key != expected_target_record_key
                or destination.storage_key != descriptor["StorageKey"]
            ):
                raise ValueError("The locked update target is stale or changed.")
            external_slots = []
            destination_storage = None
            if destination.storage_kind == "dps":
                destination_storage = self._dps_storages[destination.storage_key]
            elif destination.storage_kind == "global_palbox":
                destination_storage = self._global_palbox
            if destination_storage is not None:
                external_slots.append(
                    (destination_storage, destination.slot_index)
                )
            snapshot = self._snapshot_external_mutation(external_slots, [])
            try:
                if destination.storage_kind == "global_palbox":
                    updated_parameter = prepare_global_parameter(
                        source.pal.save_parameter, preserve_provenance=True
                    )
                    destination.pal.pal_param.clear()
                    destination.pal.pal_param.update(
                        copy.deepcopy(updated_parameter["value"])
                    )
                else:
                    incoming = copy.deepcopy(
                        source.pal.save_parameter["value"]
                    )
                    merged = restore_local_parameter_envelope(
                        incoming, destination.pal.pal_param
                    )
                    destination.pal.pal_param.clear()
                    destination.pal.pal_param.update(merged)
                destination.pal._display_name_cache = {}
                if destination_storage is not None:
                    destination_storage.dirty = True
                LOGGER.info(
                    "Global Palbox update succeeded: "
                    f"source_record={source.record_key} "
                    f"target_record={destination.record_key} "
                    f"target_storage={destination.storage_key} "
                    f"target_slot={destination.slot_index} "
                    f"pal={destination.pal.InstanceId}"
                )
                return {
                    "RecordKey": destination.record_key,
                    "StorageKey": destination.storage_key,
                    "InstanceId": str(destination.pal.InstanceId),
                }
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Global Palbox update rolled back: {traceback.format_exc()}"
                )
                raise

        if action != "clone":
            raise ValueError(f"Unsupported Global Palbox action: {action}")
        if is_import:
            target_container = self.container_data.get_container(
                descriptor["ContainerId"]
            )
            if target_container is None or target_container.get_free_slot_index() == -1:
                raise ValueError("Target world container is full or unavailable.")
            snapshot = self._snapshot_external_mutation([], [target_container])
            try:
                target_slot = target_container.add_pal(source.pal.InstanceId)
                target_obj, target_pal, target_group = self._make_world_pal(
                    source, descriptor, target_container, target_slot
                )
                target_pal.pal_param.pop(
                    "MapObjectConcreteInstanceIdAssignedToExpedition", None
                )
                if not target_group.add_pal(target_pal.InstanceId):
                    raise ValueError("Pal already exists in the target guild.")
                self._entities_list.append(target_obj)
                target_record = self.world_adapter.record(
                    target_obj,
                    storage_key=descriptor["StorageKey"],
                    slot_index=target_slot,
                    storage_owner_uid=descriptor.get("StorageOwnerPlayerUid"),
                    pal=target_pal,
                )
                self.pal_repository.register(target_record, created=True)
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Global Palbox import rolled back: {traceback.format_exc()}"
                )
                raise
        else:
            global_storage = self._global_palbox
            if global_storage is None:
                raise ValueError("Global Palbox is unavailable.")
            target_index = global_storage.free_index()
            if target_index < 0:
                raise ValueError("Global Palbox is full.")
            snapshot = self._snapshot_external_mutation(
                [(global_storage, target_index)], []
            )
            try:
                save_parameter = prepare_global_parameter(
                    source.pal.save_parameter, preserve_provenance=True
                )
                target_record = self.storage_adapters[
                    global_storage.storage_key
                ].allocate(save_parameter, source.pal.InstanceId)
                self.pal_repository.register(target_record)
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Global Palbox export rolled back: {traceback.format_exc()}"
                )
                raise
        self._container_registry_cache = None
        LOGGER.info(
            "Global Palbox clone succeeded: "
            f"source_record={source.record_key} "
            f"target_record={target_record.record_key} "
            f"target_storage={target_record.storage_key} "
            f"target_slot={target_record.slot_index} "
            f"pal={target_record.pal.InstanceId}"
        )
        return {
            "RecordKey": target_record.record_key,
            "StorageKey": target_record.storage_key,
            "InstanceId": str(target_record.pal.InstanceId),
        }

    def transfer_pal(
        self,
        source_record_key: str,
        target_storage_key: str,
        action: Literal["move", "clone", "update"],
        expected_target_record_key: str | None = None,
    ) -> dict:
        source = self.get_record(source_record_key)
        if source is None:
            raise ValueError("Source Pal record not found.")
        if source.pal.IsExpeditionPal and action == "move":
            raise ValueError("Expedition Pals must be recalled in-game before moving.")
        descriptor = self.get_storage_descriptor(target_storage_key)
        if descriptor is None:
            raise ValueError("Target storage is unknown or unsafe.")
        if (
            source.storage_kind == "global_palbox"
            or descriptor["StorageKind"] == "global_palbox"
            or action in {"clone", "update"}
        ):
            return self._transfer_global(
                source, descriptor, action, expected_target_record_key
            )
        if action != "move":
            raise ValueError(f"Unsupported transfer action: {action}")
        if not descriptor["MovableInto"]:
            raise ValueError("Target storage is unknown or unsafe.")
        target_storage_key = descriptor["StorageKey"]
        if source.storage_key == target_storage_key:
            raise ValueError("Pal is already in the target storage.")
        if source.storage_kind == "world" and source.storage_key is None:
            raise ValueError(
                "Pal is not in the container slot it records; repair it before moving."
            )

        LOGGER.info(
            "Transfer Pal requested: "
            f"action={action} source_record={source.record_key} "
            f"source_storage={source.storage_key} source_slot={source.slot_index} "
            f"pal={source.pal.InstanceId} pal_owner={source.pal.OwnerPlayerUId} "
            f"target_storage={target_storage_key} "
            f"target_kind={descriptor['StorageKind']} "
            f"storage_owner={descriptor.get('StorageOwnerPlayerUid')}"
        )

        if source.storage_kind == "world" and descriptor["StorageKind"] == "world":
            # `move_pal` re-locates the record itself, so the transfer no longer
            # patches `storage_key`/`slot_index` behind it.
            self.move_pal(source.pal.InstanceId, descriptor["ContainerId"])
            return {
                "RecordKey": source.record_key,
                "StorageKey": source.storage_key,
                "InstanceId": str(source.pal.InstanceId),
            }

        target_storage = None
        target_container = None
        target_index = -1
        if descriptor["StorageKind"] == "dps":
            target_storage = self._dps_storages.get(target_storage_key)
            if target_storage is None:
                raise ValueError("Target DPS is unavailable.")
            target_index = target_storage.free_index()
            if target_index < 0:
                raise ValueError("Target DPS is full.")
            if any(
                record.pal.InstanceId == source.pal.InstanceId
                for record in self.storage_adapters[target_storage_key].records()
            ):
                raise ValueError("Pal already exists in the target DPS.")
        elif descriptor["StorageKind"] == "world":
            target_container = self.container_data.get_container(
                descriptor["ContainerId"]
            )
            if target_container is None or target_container.get_free_slot_index() == -1:
                raise ValueError("Target world container is full or unavailable.")
            self._validate_world_target(source, descriptor)
        else:
            raise ValueError("Target storage does not support movement.")

        source_storage = (
            self._dps_storages.get(source.storage_key)
            if source.storage_kind == "dps"
            else None
        )
        source_container = None
        if source.storage_kind == "world":
            source_container = self.container_data.get_container(source.pal.ContainerId)
        external_slots = []
        if source_storage is not None:
            external_slots.append((source_storage, source.slot_index))
        if target_storage is not None:
            external_slots.append((target_storage, target_index))
        snapshot = self._snapshot_external_mutation(
            external_slots,
            [
                container
                for container in (source_container, target_container)
                if container is not None
            ],
        )

        try:
            if target_storage is not None:
                target_record = self.storage_adapters[
                    target_storage.storage_key
                ].allocate(
                    source.pal.save_parameter,
                    source.pal.InstanceId,
                )
            else:
                target_slot = target_container.add_pal(source.pal.InstanceId)
                if target_slot < 0:
                    raise ValueError("Target world container is full.")
                target_obj, target_pal, target_group = self._make_world_pal(
                    source, descriptor, target_container, target_slot
                )
                if not target_group.add_pal(target_pal.InstanceId):
                    raise ValueError("Pal already exists in the target guild.")
                self._entities_list.append(target_obj)
                target_record = self.world_adapter.record(
                    target_obj,
                    storage_key=target_storage_key,
                    slot_index=target_slot,
                    storage_owner_uid=descriptor.get("StorageOwnerPlayerUid"),
                    pal=target_pal,
                )

            if source.storage_kind == "world":
                source_container.del_pal(source.pal.InstanceId)
                source_group = self.group_data.get_group(source.group_id)
                if source_group:
                    source_group.del_pal(source.pal.InstanceId)
                self._entities_list.remove(source.native_record)
                self.add_locker_id(source.pal.InstanceId)
            else:
                self.storage_adapters[source.storage_key].clear(source.record_key)
                if descriptor["StorageKind"] == "world":
                    self.remove_locker_id(source.pal.InstanceId)

            self._unregister_record(source)
            if target_record.storage_kind == "dps":
                self._register_external_record(target_record)
            else:
                self.pal_repository.register(target_record)
            self._container_registry_cache = None
            locker_action = (
                "add"
                if source.storage_kind == "world"
                else "remove" if descriptor["StorageKind"] == "world" else "unchanged"
            )
            LOGGER.info(
                "Transfer Pal succeeded: "
                f"source_record={source.record_key} "
                f"target_record={target_record.record_key} "
                f"target_storage={target_record.storage_key} "
                f"target_slot={target_record.slot_index} "
                f"pal={target_record.pal.InstanceId} "
                f"pal_owner={target_record.pal.OwnerPlayerUId} "
                f"locker_action={locker_action}"
            )
            return {
                "RecordKey": target_record.record_key,
                "StorageKey": target_record.storage_key,
                "InstanceId": str(target_record.pal.InstanceId),
            }
        except Exception as error:
            self._restore_external_mutation(snapshot)
            LOGGER.error(
                "Transfer Pal rolled back: "
                f"source_record={source.record_key} "
                f"target_storage={target_storage_key} "
                f"pal={source.pal.InstanceId}; error={error}\n"
                f"{traceback.format_exc()}"
            )
            raise

    def move_pal(
        self,
        pal_id: UUID | str,
        target_container_ids: UUID | str | list[UUID | str],
    ) -> bool:
        candidate_ids = (
            target_container_ids
            if isinstance(target_container_ids, list)
            else [target_container_ids]
        )
        target_ids_text = ",".join(
            str(candidate_id) for candidate_id in candidate_ids
        )

        def reject(reason: str, details: str = "") -> None:
            suffix = f"; {details}" if details else ""
            LOGGER.warning(
                f"Move Pal rejected: pal={pal_id} targets=[{target_ids_text}]"
                f"{suffix}; reason={reason}"
            )
            raise ValueError(reason)

        pal_entity = self.get_pal(pal_id)
        if pal_entity is None:
            reject("Pal not found.")
        pal_record = self.get_record(f"world:{pal_entity.InstanceId}")
        if pal_entity.IsExpeditionPal:
            reject("Expedition Pals must be recalled in-game before moving.")

        # A World record only keeps its storage key if it really occupies the slot it
        # records, so this is the whole location precondition the move needs.
        if pal_record is None or pal_record.storage_key is None:
            reject("Pal is not in the container slot it records; repair it first.")

        source_text = f"{pal_entity.ContainerId}@{pal_entity.SlotIndex}"
        LOGGER.info(
            f"Move Pal requested: pal={pal_entity.InstanceId} source={source_text} "
            f"owner={pal_entity.OwnerPlayerUId} targets=[{target_ids_text}]"
        )

        registry = self._container_descriptor_map()
        target_descriptor = None
        target_container = None
        candidate_statuses = []
        for candidate_id in candidate_ids:
            descriptor = registry.get(str(candidate_id))
            container = self.container_data.get_container(candidate_id)
            exists = container is not None
            occupied = len(container.slots) if exists else None
            size = container.size if exists else None
            movable = bool(descriptor and descriptor["MovableInto"])
            candidate_statuses.append(
                f"container={candidate_id} exists={exists} "
                f"kind={descriptor['ContainerKind'] if descriptor else 'unknown'} "
                f"occupied={occupied}/{size} movable={movable}"
            )
            if (
                descriptor
                and descriptor["MovableInto"]
                and container is not None
                and len(container.slots) < container.size
            ):
                target_descriptor = descriptor
                target_container = container
                break
        if target_descriptor is None or target_container is None:
            reject(
                "Target container is unknown, unsafe, or full.",
                f"candidates=[{'; '.join(candidate_statuses)}]",
            )

        source_container = self.container_data.get_container(pal_entity.ContainerId)
        if source_container is None:
            reject("Source container is unavailable.", f"source={source_text}")
        if str(source_container.ID) == str(target_container.ID):
            reject("Pal is already in the target container.", f"source={source_text}")
        if target_container.has_pal(pal_entity.InstanceId):
            reject("Pal already exists in the target container.")
        target_is_shared = target_descriptor.get("Shared", False)
        if target_is_shared and pal_entity.OwnerPlayerUId is None:
            reject("A shared container requires a Pal with an owner.")
        if (
            not target_is_shared
            and str(pal_record.group_id) != str(target_descriptor.get("GroupId"))
        ):
            reject("Cross-guild Pal movement is not supported.")

        source_slot = source_container.get_slot(pal_entity.InstanceId)
        if source_slot is None:
            reject("Source slot is unavailable.", f"source={source_text}")

        source_snapshot = source_container.snapshot_slots()
        target_snapshot = target_container.snapshot_slots()
        pal_param_snapshot = copy.deepcopy(pal_entity.pal_param)
        storage_key_snapshot = pal_record.storage_key
        slot_index_snapshot = pal_record.slot_index
        registry_snapshot = self._container_registry_cache

        try:
            target_slot_index = target_container.add_slot_copy(source_slot)
            if target_slot_index == -1:
                raise ValueError("Target container has no free slot.")
            source_container.del_pal(pal_entity.InstanceId)
            if source_container.has_pal(pal_entity.InstanceId):
                raise RuntimeError("Failed removing the source slot.")
            pal_entity.SlotId = (target_container.ID, target_slot_index)
            # The record's location mirrors the Pal's slot, so the two move together
            # and the repository's storage index never points at the container the
            # Pal just left. Until F3b only the transfer path patched this up
            # afterwards, so a plain move left the record on its old storage key.
            pal_record.storage_key = WorldPalAdapter.storage_key(target_container.ID)
            pal_record.slot_index = pal_entity.SlotIndex

            old_owner_id = (
                str(pal_entity.OwnerPlayerUId) if pal_entity.OwnerPlayerUId else None
            )
            target_owner_id = target_descriptor.get("OwnerPlayerUId")
            if target_descriptor["ContainerKind"] == "base":
                set_owner(pal_entity, None)
            elif not target_is_shared:
                # A shared container keeps whoever already owned the Pal.
                target_owner = self.get_player(target_owner_id)
                if target_owner is None:
                    raise ValueError("Target container owner is unavailable.")
                set_owner(pal_entity, target_owner.PlayerUId)

            # Owner and location both changed, and every roster reads through those
            # indexes, so they are rebuilt once the move is settled.
            self.pal_repository.reindex()
            self._container_registry_cache = None
            LOGGER.info(
                f"Move Pal succeeded: pal={pal_entity.InstanceId} "
                f"source={source_text} target={target_container.ID}@{target_slot_index} "
                f"owner={old_owner_id}->{pal_entity.OwnerPlayerUId}"
            )
            return True
        except Exception as error:
            source_container.restore_slots(source_snapshot)
            target_container.restore_slots(target_snapshot)
            pal_entity.pal_param.clear()
            pal_entity.pal_param.update(pal_param_snapshot)
            pal_record.storage_key = storage_key_snapshot
            pal_record.slot_index = slot_index_snapshot
            self.pal_repository.reindex()
            self._container_registry_cache = registry_snapshot
            LOGGER.error(
                f"Move Pal rolled back: pal={pal_entity.InstanceId} "
                f"source={source_text} target={target_container.ID} "
                f"owner={pal_entity.OwnerPlayerUId}; error={error}\n"
                f"{traceback.format_exc()}"
            )
            raise
    
    def delete_pal(self, record_key: str) -> bool:
        record = self.get_record(record_key)
        if record is not None and record.storage_kind == "global_palbox":
            storage = self._global_palbox
            snapshot = self._snapshot_external_mutation(
                [(storage, record.slot_index)], []
            )
            try:
                self.storage_adapters[record.storage_key].clear(record.record_key)
                self._unregister_record(record)
                self._container_registry_cache = None
                LOGGER.info(
                    "Deleted Global Palbox Pal: "
                    f"record={record.record_key} slot={record.slot_index} "
                    f"pal={record.pal.InstanceId}"
                )
                return True
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Failed deleting Global Palbox Pal {record.record_key}: "
                    f"{traceback.format_exc()}"
                )
                return False
        if record is not None and record.storage_kind == "dps":
            storage = self._dps_storages.get(record.storage_key)
            if storage is None:
                return False
            snapshot = self._snapshot_external_mutation(
                [(storage, record.slot_index)], []
            )
            try:
                self.storage_adapters[record.storage_key].clear(record.record_key)
                self.remove_locker_id(record.pal.InstanceId)
                self._unregister_record(record)
                self._container_registry_cache = None
                LOGGER.info(
                    "Deleted DPS Pal: "
                    f"record={record.record_key} storage={record.storage_key} "
                    f"slot={record.slot_index} pal={record.pal.InstanceId} "
                    "locker_action=remove"
                )
                return True
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Failed deleting DPS Pal {record.record_key}: "
                    f"{traceback.format_exc()}"
                )
                return False

        world_record = record
        if world_record is None:
            LOGGER.warning(f"Can't find pal {record_key}")
            return False
        # The record is the Pal's location; the baseworker and dangling maps it may
        # also appear in are cleared by `_unregister_record` once the delete lands.
        popped_pal = world_record.pal
        try:
            if pal_group := self.group_data.get_group(world_record.group_id):
                pal_group.del_pal(popped_pal.InstanceId)
            if (
                pal_container := self.container_data.get_container(popped_pal.ContainerId)
            ) is not None:
                pal_container.del_pal(popped_pal.InstanceId)
            self._entities_list.remove(world_record.native_record)
        except:
            LOGGER.warning(
                f"Error Deleting PAL {record_key}: {traceback.format_exc()}"
            )
            return False
        self._unregister_record(world_record)
        self._container_registry_cache = None
        LOGGER.info(f"DELETED PAL {record_key}")
        return True

    def creation_targets(self, roster_key: str) -> list[dict]:
        roster_key = str(roster_key)
        descriptors = self.get_container_registry()
        if roster_key == "PAL_BASE_WORKER_BTN":
            return [
                descriptor
                for descriptor in descriptors
                if descriptor["ContainerKind"] == "base"
                and descriptor["MovableInto"]
            ]
        if roster_key == "PAL_GLOBAL_STORAGE_BTN":
            return [
                descriptor
                for descriptor in descriptors
                if descriptor["StorageKind"] == "global_palbox"
                and descriptor["CloneableInto"]
            ]
        player = self.get_player(roster_key)
        if player is None:
            return []
        return [
            descriptor
            for descriptor in descriptors
            if (
                descriptor["StorageKind"] == "world"
                and descriptor["ContainerKind"] in {"party", "storage"}
                and descriptor.get("OwnerPlayerUId") == roster_key
            )
            or (
                descriptor["StorageKind"] == "dps"
                and descriptor.get("StorageOwnerPlayerUid") == roster_key
            )
        ]

    def create_pal(
        self,
        roster_key: str,
        target_storage_key: str,
        save_parameter: dict | None = None,
        pal_owner_uid: str | UUID | None = None,
    ) -> PalRecord:
        """Create one Pal in `target_storage_key`, in that storage own native format.

        `save_parameter` is the complete gameplay payload the new Pal is copied
        from -- a live Pal, a template, an imported record -- or None for a default
        Pal. It is the only thing a source contributes: identity, owner, guild and
        position are the target storage to decide, which is what makes a template
        made from a Global Palbox Pal creatable into a player Palbox (spec §6.3).
        """
        allowed = {
            descriptor["StorageKey"]: descriptor
            for descriptor in self.creation_targets(roster_key)
        }
        descriptor = allowed.get(str(target_storage_key))
        if descriptor is None:
            raise ValueError("Target storage is not valid for this roster.")
        if descriptor["StorageKind"] == "world":
            player_uid = (
                roster_key
                if roster_key != "PAL_BASE_WORKER_BTN"
                else descriptor.get("OwnerPlayerUId")
            )
            record = self.add_pal(
                player_uid,
                save_parameter,
                descriptor["ContainerId"],
            )
            if record is None:
                raise ValueError("Unable to create Pal in target container.")
            return record
        if descriptor["StorageKind"] == "global_palbox":
            storage = self._global_palbox
            if storage is None:
                raise ValueError("Global Palbox is unavailable.")
            target_index = storage.free_index()
            if target_index < 0:
                raise ValueError("Global Palbox is full.")
            snapshot = self._snapshot_external_mutation(
                [(storage, target_index)], []
            )
            try:
                instance_id = self._unused_instance_id()
                # No World record is built on the way: a Global Palbox Pal is a
                # parameter in a preallocated slot, and normalizing it is what
                # clears the position and provenance a copied payload arrives with.
                record = self.storage_adapters[storage.storage_key].allocate(
                    prepare_global_parameter(
                        save_parameter
                        if save_parameter is not None
                        else PalObjects.DefaultPalSaveParameter(
                            PalObjects.EMPTY_UUID, PalObjects.EMPTY_UUID, -1
                        ),
                        preserve_provenance=False,
                    ),
                    instance_id,
                )
                self.pal_repository.register(record, created=True)
                self._container_registry_cache = None
                LOGGER.info(
                    "Created Global Palbox Pal: "
                    f"record={record.record_key} slot={record.slot_index} "
                    f"pal={record.pal.InstanceId}"
                )
                return record
            except Exception:
                self._restore_external_mutation(snapshot)
                LOGGER.error(
                    f"Failed creating Global Palbox Pal: {traceback.format_exc()}"
                )
                raise
        if descriptor["StorageKind"] != "dps":
            raise ValueError("Creation for this storage is not implemented yet.")

        storage_owner = self.get_player(roster_key)
        player = self.get_player(pal_owner_uid) if pal_owner_uid else storage_owner
        storage = self._dps_storages.get(descriptor["StorageKey"])
        if storage_owner is None or player is None or storage is None:
            raise ValueError("DPS owner or storage is unavailable.")
        target_index = storage.free_index()
        if target_index < 0:
            raise ValueError("Target DPS is full.")
        snapshot = self._snapshot_external_mutation(
            [(storage, target_index)], []
        )
        try:
            instance_id = self._unused_instance_id()
            record = self.storage_adapters[storage.storage_key].allocate(
                save_parameter
                if save_parameter is not None
                else PalObjects.DefaultPalSaveParameter(
                    player.PlayerUId, PalObjects.EMPTY_UUID, -1
                ),
                instance_id,
            )
            # The slot is the Pal now, so the rest is written through it rather than
            # onto a scratch record: whatever the payload said about where it lived
            # and who owned it belongs to wherever it came from.
            pal = record.pal
            pal.SlotId = (PalObjects.EMPTY_UUID, -1)
            set_owner(pal, player.PlayerUId)
            pal.pal_param.pop(
                "MapObjectConcreteInstanceIdAssignedToExpedition", None
            )
            self.add_locker_id(instance_id)
            self._register_external_record(record, created=True)
            self._container_registry_cache = None
            LOGGER.info(
                "Created DPS Pal: "
                f"record={record.record_key} storage={record.storage_key} "
                f"slot={record.slot_index} pal={record.pal.InstanceId} "
                f"pal_owner={record.pal.OwnerPlayerUId} locker_action=add"
            )
            return record
        except Exception:
            self._restore_external_mutation(snapshot)
            LOGGER.error(f"Failed creating DPS Pal: {traceback.format_exc()}")
            raise

    def duplicate_pal(self, record_key: str, roster_key: str) -> PalRecord:
        source = self.get_record(record_key)
        if source is None:
            raise ValueError("Selected Pal not found.")
        # The whole of what a copy inherits: every gameplay field the source has,
        # including the ones this editor has never heard of.
        source_parameter = source.pal.save_parameter

        if source.storage_kind == "global_palbox":
            clone = self.create_pal(
                "PAL_GLOBAL_STORAGE_BTN",
                source.storage_key,
                source_parameter,
            )
        elif source.storage_kind == "dps":
            storage = self._dps_storages.get(source.storage_key)
            if storage is None:
                raise ValueError("Source DPS is unavailable.")
            clone = self.create_pal(
                str(storage.owner_uid),
                source.storage_key,
                source_parameter,
                pal_owner_uid=source.pal.OwnerPlayerUId,
            )
        else:
            targets = [
                descriptor
                for descriptor in self.creation_targets(roster_key)
                if descriptor["StorageKind"] == "world"
                and descriptor["ContainerKind"] in {"base", "party", "storage"}
                and descriptor["Occupied"] < descriptor["Capacity"]
            ]
            if not targets:
                raise ValueError("The target Pal containers are full.")
            clone = self.create_pal(
                roster_key,
                targets[0]["StorageKey"],
                source_parameter,
            )

        LOGGER.info(
            "Duplicated Pal: "
            f"source_record={source.record_key} "
            f"source_storage={source.storage_key} "
            f"source_pal={source.pal.InstanceId} "
            f"target_record={clone.record_key} "
            f"target_storage={clone.storage_key} "
            f"target_slot={clone.slot_index} "
            f"target_pal={clone.pal.InstanceId} "
            f"owner={clone.pal.OwnerPlayerUId}"
        )
        return clone
    
    def heal_all_pals(self):
        # Every base worker and dangling Pal is a registered record too, so one pass
        # over the repository covers what three passes over three collections did --
        # plus the Global Palbox, which the old palbox-shaped scan could not reach.
        for record in self.pal_repository.records():
            record.pal.heal_pal()
            # Global Palbox and DPS Pals live outside the world save, so a heal that
            # skips this is discarded when the session is written -- the same
            # normalization every single-Pal edit does, owed to every Pal here too.
            self.normalize_external_record(record)
            self.pal_repository.mark_modified(record)
    
    def add_pal(
        self,
        player_uid: str | UUID,
        save_parameter: dict = None,
        target_container_id: str | UUID = None,
    ) -> Optional[PalRecord]:
        requested_player = self.get_player(player_uid)
        owner_player = requested_player
        historical_player = requested_player
        target_descriptor = None

        if target_container_id is not None:
            target_descriptor = self._container_descriptor_map().get(
                str(target_container_id)
            )
            if target_descriptor is None or not target_descriptor["MovableInto"]:
                LOGGER.warning(f"Unsafe target container {target_container_id}")
                return None
            pal_container = self.container_data.get_container(target_container_id)
            if pal_container is None or pal_container.get_free_slot_index() == -1:
                LOGGER.info("No Empty Pal Slot")
                return None
            group_id = target_descriptor.get("GroupId")
            owner_id = target_descriptor.get("OwnerPlayerUId")
            owner_player = self.get_player(owner_id) if owner_id else None
            if target_descriptor["ContainerKind"] != "base" and owner_player is None:
                LOGGER.warning("Target container owner not found")
                return None
            if requested_player and str(requested_player.group_id) != str(group_id):
                LOGGER.warning("Cross-guild Pal creation is unsupported")
                return None
            historical_player = owner_player or (
                requested_player
                if requested_player and str(requested_player.group_id) == str(group_id)
                else next(
                    (
                        player
                        for player in self.get_players()
                        if str(player.group_id) == str(group_id)
                    ),
                    None,
                )
            )
        else:
            if requested_player is None:
                LOGGER.warning(f"Player {player_uid} not found")
                return None
            group_id = requested_player.group_id
            pal_container = next(
                (
                    container
                    for container_id in (
                        requested_player.OtomoCharacterContainerId,
                        requested_player.PalStorageContainerId,
                    )
                    if (
                        container := self.container_data.get_container(container_id)
                    ) is not None
                    and container.get_free_slot_index() != -1
                ),
                None,
            )

        if pal_container is None or historical_player is None:
            LOGGER.info("No valid Pal target or historical owner")
            return None

        group = self.group_data.get_group(group_id)
        if group is None:
            LOGGER.warning(f"Group {group_id} not found")
            return None

        pal_instanceId = self._unused_instance_id(pal_container, group)
        container_id = pal_container.ID
        pal_obj = None
        container_added = group_added = False
        try:
            slot_idx = pal_container.add_pal(pal_instanceId)
            if slot_idx == -1:
                return None
            container_added = True
            pal_obj = WorldPalAdapter.native_record(
                save_parameter,
                instance_id=pal_instanceId,
                owner_uid=historical_player.PlayerUId,
                container_id=container_id,
                slot_index=slot_idx,
                group_id=group_id,
            )
            pal_entity = WorldPalAdapter.entity(pal_obj)
            if save_parameter is not None:
                # It seems the item container id is not necessarily referenced in the ItemContainerSaveData
                # so just assign a randomly for now.
                pal_entity.pal_param["EquipItemContainerId"] = (
                    PalObjects.PalContainerId(str(uuid.uuid4()))
                )

            historical_uid = historical_player.PlayerUId
            pal_entity.pal_param["OldOwnerPlayerUIds"] = PalObjects.ArrayProperty(
                "StructProperty",
                {
                    "prop_name": "OldOwnerPlayerUIds",
                    "prop_type": "StructProperty",
                    "values": [toUUID(historical_uid)],
                    "type_name": "Guid",
                    "id": PalObjects.EMPTY_UUID,
                },
            )
            pal_entity.pal_param["LastNickNameModifierPlayerUid"] = (
                PalObjects.Guid(historical_uid)
            )
            if owner_player is None:
                set_owner(pal_entity, None)
            else:
                set_owner(pal_entity, owner_player.PlayerUId)
            pal_entity.pal_param.pop(
                "MapObjectConcreteInstanceIdAssignedToExpedition", None
            )

            if not group.add_pal(pal_instanceId):
                raise ValueError("Duplicated Pal ID in group")
            group_added = True
            self._entities_list.append(pal_obj)

            record = self.world_adapter.record(
                pal_obj,
                storage_key=WorldPalAdapter.storage_key(pal_container.ID),
                slot_index=slot_idx,
                storage_owner_uid=(
                    str(owner_player.PlayerUId) if owner_player else None
                ),
                pal=pal_entity,
            )
            # Every creation entry point registers here, so a Pal made through the CLI
            # or through `create_pal` is tracked the same way -- and marked created,
            # which is what settles its capture count and paldeck flag on save.
            self.pal_repository.register(record, created=True)
        except Exception:
            if pal_obj in self._entities_list:
                self._entities_list.remove(pal_obj)
            if group_added:
                group.del_pal(pal_instanceId)
            if container_added:
                pal_container.del_pal(pal_instanceId)
            LOGGER.error(f"Failed adding pal: {traceback.format_exc()}")
            return None
        self._container_registry_cache = None
        LOGGER.info(f"Added Pal {pal_entity} to container {pal_container.ID}")
        return record
