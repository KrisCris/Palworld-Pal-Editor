import copy
from datetime import datetime
from pathlib import Path
import re
import shutil
import traceback
from typing import Optional
import uuid

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import FArchiveReader, FArchiveWriter, UUID
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES, PALWORLD_TYPE_HINTS

from palworld_pal_editor.core.basecamp_data import BaseCampData

from palworld_pal_editor.core.container_data import ContainerData
from palworld_pal_editor.core.item_container_data import ItemContainerData

from palworld_pal_editor.core.pal_objects import PalObjects, UUID2HexStr, toUUID
from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_storage import FixedPalStorage, PalRecordRef
from palworld_pal_editor.utils import LOGGER, DataProvider, alphanumeric_key
from palworld_pal_editor.core.group_data import GroupData


def skip_decode(reader: FArchiveReader, type_name: str, size: int, path: str):
    if type_name == "ArrayProperty":
        array_type = reader.fstring()
        value = {
            "skip_type": type_name,
            "array_type": array_type,
            "id": reader.optional_guid(),
            "value": reader.read(size),
        }
    elif type_name == "MapProperty":
        key_type = reader.fstring()
        value_type = reader.fstring()
        _id = reader.optional_guid()
        value = {
            "skip_type": type_name,
            "key_type": key_type,
            "value_type": value_type,
            "id": _id,
            "value": reader.read(size),
        }
    elif type_name == "StructProperty":
        value = {
            "skip_type": type_name,
            "struct_type": reader.fstring(),
            "struct_id": reader.guid(),
            "id": reader.optional_guid(),
            "value": reader.read(size),
        }
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {type_name} in {path}"
        )
    return value


def skip_encode(writer: FArchiveWriter, property_type: str, properties: dict) -> int:
    if "skip_type" not in properties:
        if properties["custom_type"] in PALWORLD_CUSTOM_PROPERTIES is not None:
            return PALWORLD_CUSTOM_PROPERTIES[properties["custom_type"]][1](
                writer, property_type, properties
            )
        else:
            # Never be run to here
            return writer.property_inner(writer, property_type, properties)
    if property_type == "ArrayProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["array_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "MapProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["key_type"])
        writer.fstring(properties["value_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "StructProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["struct_type"])
        writer.guid(properties["struct_id"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {property_type}"
        )


MAIN_SKIP_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
MAIN_SKIP_PROPERTIES[".worldSaveData.MapObjectSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.FoliageGridSaveDataMap"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.MapObjectSpawnerInStageSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.WorkSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.DungeonSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.EnemyCampSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.CharacterParameterStorageSaveData"] = (skip_decode, skip_encode)

MAIN_SKIP_PROPERTIES[".worldSaveData.InvaderSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.DungeonPointMarkerSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.GameTimeSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.FixedWeaponDestroySaveData"] = (skip_decode, skip_encode)

MAIN_SKIP_PROPERTIES[".worldSaveData.OilrigSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.SupplySaveData"] = (skip_decode, skip_encode)

MAIN_SKIP_PROPERTIES[".worldSaveData.RandomizerSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.GuildExtraSaveDataMap"] = (skip_decode, skip_encode)


PLAYER_SKIP_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PLAYER_SKIP_PROPERTIES[".SaveData.PlayerCharacterMakeData"] = (skip_decode, skip_encode)
PLAYER_SKIP_PROPERTIES[".SaveData.LastTransform"] = (skip_decode, skip_encode)
# PLAYER_SKIP_PROPERTIES[".SaveData.RecordData"] = (skip_decode, skip_encode)

class SaveManager:
    # Although these are class attrs, SaveManager itself is singleton so it should be fine?
    _instance = None
    _file_path: Optional[Path]
    _raw_gvas: Optional[bytes]
    _save_type: Optional[int]

    gvas_file: Optional[GvasFile]
    _entities_list: Optional[list[dict]]

    player_mapping: Optional[dict[str, PlayerEntity]]
    baseworker_mapping: Optional[dict[str, PalEntity]]
    _dangling_pals: Optional[dict[str, PalEntity]]
    
    container_data: Optional[ContainerData]
    item_container_data: Optional[ItemContainerData]
    group_data: Optional[GroupData]
    camp_data: Optional[BaseCampData]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
                
    def open(self, file_path: str) -> Optional[GvasFile]:
        self._file_path = Path(file_path).resolve()
        self._record_mapping: dict[str, PalRecordRef] = {}
        self._records_by_instance: dict[str, list[PalRecordRef]] = {}
        self._roster_record_keys: dict[str, list[str]] = {}
        self._dps_storages: dict[str, FixedPalStorage] = {}
        self._global_palbox: FixedPalStorage | None = None
        self.load_warnings: list[str] = []

        level_sav_path = self._file_path / "Level.sav"

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

            self._load_entities()
            self._register_world_records()
            self._load_external_storages()
            self._container_registry_cache = None

            LOGGER.info("Done")
        return self.gvas_file

    def save(self, file_path: str) -> bool:
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
            
        file_path: Path = output_path / "Level.sav"

        if output_path.exists():
            BK_FOLDER_NAME = "Palworld-Pal-Editor-Backup"
            backup_dir = output_path / BK_FOLDER_NAME / f"{datetime.now().strftime(r'%Y-%m-%d_%H-%M-%S')}"
            try:
                if output_path.exists():
                    LOGGER.info(f"Saving backup of {output_path} to {backup_dir}")
                    shutil.copytree(self._file_path, backup_dir, 
                                    ignore=lambda dir, files: [f for f in files if not f == "Players" and not f.endswith('.sav')])
                else:
                    LOGGER.info(f"No existing directory to backup: {output_path}")
            except Exception as e:
                LOGGER.error(f"Error backing up directory: {e}")
                return False

        LOGGER.info("Saving Player Data...")
        for player in self.player_mapping.values():
            self.save_player_sav(player, output_path)

        LOGGER.info("Saving Level.sav...")
        gvas_file = copy.deepcopy(self.gvas_file)
        LOGGER.info("Compressing Main GVAS file")
        sav_data = compress_gvas_to_sav(
            gvas_file.write(MAIN_SKIP_PROPERTIES), self._save_type
        )

        LOGGER.info(f"Saving to {file_path}")
        with file_path.open("wb") as file:
            file.write(sav_data)
        LOGGER.info(f"Saved to {file_path}")
        return True
    
    def load_player_sav(self, player_uid: str | UUID) -> GvasFile:
        player_path: Path = self._file_path / "Players" / f"{UUID2HexStr(player_uid)}.sav"
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

        player_entity.save_new_pal_records()
        gvas_file, compression_times = player_entity.PlayerGVAS
        output_path = (save_path or self._file_path) / "Players"
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
    
    def _load_entities(self):
        self.player_mapping = {}
        self._dangling_pals = {}
        self.baseworker_mapping = {}
        base_container_ids = {
            str(camp.container_id)
            for camp in self.camp_data.get_camps()
            if camp.container_id
        }
        temp_player_pal_mapping: dict[str, dict[str, PalEntity]] = {}
        for entity in self._entities_list:
            entity_struct = entity["value"]["RawData"]["value"]["object"]["SaveParameter"]
            if entity_struct['struct_type'] != 'PalIndividualCharacterSaveParameter':
                LOGGER.warning(f"Non-player/pal data found in CharacterSaveParameterMap, skipping {entity}")
                continue

            entity_param: dict = entity_struct['value']
            try: 
                if PalObjects.get_BaseType(entity_param.get("IsPlayer")):
                    uid_str = str(PalObjects.get_BaseType(entity["key"].get("PlayerUId")))
                    nickname = str(PalObjects.get_BaseType(entity_param.get("NickName")))
                    LOGGER.info(f"Players found: {nickname} - {uid_str}")
                    if uid_str in self.player_mapping:
                        LOGGER.error(f"Duplicated player found: \n\t{self.player_mapping[uid_str]}, skipping...")
                        continue
                    
                    group_id = self.group_data.get_player_group_id(uid_str)

                    if group_id is None:
                        LOGGER.warning(f"Player {uid_str} has no guild id")
                        continue

                    player_gvas_file, player_compress_times = self.load_player_sav(uid_str)

                    if uid_str in temp_player_pal_mapping:
                        player_entity = PlayerEntity(group_id, entity, temp_player_pal_mapping[uid_str], player_gvas_file, player_compress_times)
                        del temp_player_pal_mapping[uid_str]
                    else:
                        player_entity = PlayerEntity(group_id, entity, dict(), player_gvas_file, player_compress_times)
                
                    self.player_mapping[uid_str] = player_entity
                    LOGGER.info(f"Player Object Created: {player_entity}")
                else:
                    pal_entity = PalEntity(entity)
                    container_id, slot_idx = pal_entity.SlotId
                    group_id = pal_entity.group_id
                    actual_slots = self.container_data.find_pal_slots(
                        pal_entity.InstanceId
                    )
                    is_unref_pal = not (
                        len(actual_slots) == 1
                        and str(actual_slots[0][0].ID) == str(container_id)
                        and actual_slots[0][1].inv_idx == slot_idx
                    )
                    if is_unref_pal:
                        LOGGER.info(f"Likely Ghost Pal: {pal_entity}")
                    pal_entity.is_unreferenced_pal = is_unref_pal

                    owner = pal_entity.OwnerPlayerUId
                    if owner:
                        owner_str = str(owner)
                        if owner_str in self.player_mapping:
                            self.player_mapping[owner_str].add_pal(
                                pal_entity, f"world:{pal_entity.InstanceId}"
                            )
                        else:
                            temp_player_pal_mapping.setdefault(owner_str, dict())[
                                f"world:{pal_entity.InstanceId}"
                            ] = pal_entity
                        LOGGER.info(f"Found pal: {pal_entity}")

                    else:
                        if (
                            len(actual_slots) == 1
                            and str(actual_slots[0][0].ID) in base_container_ids
                        ):
                            self.baseworker_mapping[str(pal_entity.InstanceId)] = pal_entity
                            continue
                        self._dangling_pals[str(pal_entity.InstanceId)] = pal_entity
                        LOGGER.error(f"Found dangling pal object: {pal_entity}, skipping")
                        continue

            except Exception as e:
                LOGGER.error(f"Error occured while init'in object: {e}, skipping")
                continue

        
        for player in self.player_mapping.values():
            LOGGER.newline()
            LOGGER.info(f"{player}")
            sorted_palbox = player.get_sorted_pals()
            for pal in sorted_palbox:
                LOGGER.info(f"\t{pal}")
        
        LOGGER.newline()
        LOGGER.info("Pals possibly working at the base: ")
        for pal in self.get_working_pals():
            LOGGER.info(f"\t{pal}")

        LOGGER.newline()
        LOGGER.info("Dangling Pals (No OwnerID and OldOwnerID): ")
        for pal in self._dangling_pals.values():
            LOGGER.warning(f"\t{pal}")

        for uid_str in temp_player_pal_mapping:
            pal_list = temp_player_pal_mapping[uid_str]
            LOGGER.newline()
            LOGGER.warning(f"Found dangling pals owned by non-existing user {uid_str}")
            for pal in pal_list.values():
                self._dangling_pals[str(pal.InstanceId)] = pal
                LOGGER.warning(f"\t{pal}")

    @property
    def has_global_palbox(self) -> bool:
        return self._global_palbox is not None

    def _register_record(self, record: PalRecordRef, roster_key: str) -> None:
        if record.record_key in self._record_mapping:
            raise ValueError(f"Duplicated Pal RecordKey: {record.record_key}")
        self._record_mapping[record.record_key] = record
        instance_id = str(record.pal.InstanceId)
        self._records_by_instance.setdefault(instance_id, []).append(record)
        self._roster_record_keys.setdefault(roster_key, []).append(record.record_key)

    def _register_world_records(self) -> None:
        for player in self.get_players():
            roster_key = str(player.PlayerUId)
            for pal in player.get_pals():
                self._register_world_record(pal, roster_key)
        for pal in self.baseworker_mapping.values():
            self._register_world_record(pal, "PAL_BASE_WORKER_BTN")
        for pal in self._dangling_pals.values():
            self._register_world_record(pal, "PAL_OTHER_PAL_BTN")

    def _register_world_record(self, pal: PalEntity, roster_key: str) -> None:
        container_id = str(pal.ContainerId) if pal.ContainerId else None
        self._register_record(
            PalRecordRef(
                record_key=f"world:{pal.InstanceId}",
                storage_key=(
                    f"world-container:{container_id}"
                    if container_id
                    else "world-anomaly"
                ),
                storage_kind="world",
                slot_index=pal.SlotIndex if pal.SlotIndex is not None else -1,
                pal=pal,
                storage_owner_uid=(
                    str(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None
                ),
            ),
            roster_key,
        )

    def _load_external_storages(self) -> None:
        players_path = self._file_path / "Players"
        for dps_path in sorted(players_path.glob("*_dps.sav")):
            owner_hex = dps_path.stem.removesuffix("_dps")
            try:
                owner_uid = toUUID(str(uuid.UUID(owner_hex)))
                storage = FixedPalStorage.open(dps_path, "dps", owner_uid)
                self._dps_storages[storage.storage_key] = storage
                LOGGER.info(
                    f"Loaded DPS: path={dps_path} owner={owner_uid} "
                    f"occupied={storage.occupied}/{storage.capacity}"
                )
                for record in storage.records():
                    owner = self.get_player(record.pal.OwnerPlayerUId)
                    roster_key = "PAL_OTHER_PAL_BTN"
                    if owner is not None:
                        record.pal.group_id = owner.group_id
                        owner.add_pal(record.pal, record.record_key)
                        roster_key = str(owner.PlayerUId)
                    self._register_record(record, roster_key)
            except Exception as error:
                warning = f"Unable to load DPS {dps_path}: {error}"
                self.load_warnings.append(warning)
                LOGGER.warning(warning)

        gps_path = self._file_path.parent / "GlobalPalStorage.sav"
        if not gps_path.exists():
            return
        try:
            self._global_palbox = FixedPalStorage.open(
                gps_path, "global_palbox"
            )
            LOGGER.info(
                f"Loaded Global Palbox: path={gps_path} "
                f"occupied={self._global_palbox.occupied}/"
                f"{self._global_palbox.capacity}"
            )
            for record in self._global_palbox.records():
                self._register_record(record, "PAL_GLOBAL_STORAGE_BTN")
        except Exception as error:
            warning = f"Unable to load Global Palbox {gps_path}: {error}"
            self.load_warnings.append(warning)
            LOGGER.warning(warning)
            self._global_palbox = None

    def get_record(self, record_key: str) -> Optional[PalRecordRef]:
        return self._record_mapping.get(str(record_key))

    def records_by_instance(
        self, instance_id: UUID | str, domain: str = "all"
    ) -> list[PalRecordRef]:
        records = list(self._records_by_instance.get(str(instance_id), []))
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

    def records_for_roster(self, roster_key: str) -> list[PalRecordRef]:
        return [
            self._record_mapping[key]
            for key in self._roster_record_keys.get(str(roster_key), [])
        ]

    def get_players(self) -> list[PlayerEntity]:
        return self.player_mapping.values()
    
    def get_player(self, guid: UUID | str) -> Optional[PlayerEntity]:
        if guid is None: return
        guid = str(guid)
        if guid in self.player_mapping:
            player = self.player_mapping[guid]
            return player
        # LOGGER.warning(f"Player {guid} not exist")

    def get_players_by_name(self, name: str) -> list[PlayerEntity]:
        return [player for player in self.get_players() if player.NickName == name]
    
    def get_working_pal(self, guid: UUID | str) -> Optional[PalEntity]:
        return self.baseworker_mapping.get(str(guid), None)

    def get_pal(self, guid: UUID | str) -> Optional[PalEntity]:
        guid = str(guid)
        if guid in self.baseworker_mapping:
            return self.baseworker_mapping[guid]
        if guid in self._dangling_pals:
            return self._dangling_pals[guid]
        for player in self.get_players():
            if pal := player.get_pal(guid, disable_warning=True):
                return pal

        LOGGER.warning(f"Can't find pal {guid}")

    def get_working_pals(self) -> list[PalEntity]:
        return sorted(self.baseworker_mapping.values(), key=lambda pal: (alphanumeric_key(pal.PalDeckID), pal.Level or 1))

    def _container_descriptor_map(self) -> dict[str, dict]:
        cached = getattr(self, "_container_registry_cache", None)
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

        dps_name = DataProvider.get_tech_i18n("DimensionPalStorage") or (
            "Dimensional Pal Storage"
        )
        for storage in getattr(self, "_dps_storages", {}).values():
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

        global_palbox = getattr(self, "_global_palbox", None)
        if global_palbox is not None:
            storage = global_palbox
            descriptors[storage.storage_key] = {
                "ContainerId": None,
                "StorageKey": storage.storage_key,
                "StorageKind": "global_palbox",
                "ContainerKind": "global_palbox",
                "ContainerLabel": (
                    DataProvider.get_tech_i18n("GlobalPalStorage")
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

    def resolve_record_location(self, record: PalRecordRef | str) -> dict:
        record_ref = record if isinstance(record, PalRecordRef) else self.get_record(record)
        if record_ref is None:
            raise ValueError("Pal record not found")
        if record_ref.storage_kind == "world":
            location = self.resolve_pal_location(record_ref.pal)
            location["StorageKey"] = record_ref.storage_key
            location["StorageKind"] = "world"
            return location
        descriptor = self.get_storage_descriptor(record_ref.storage_key)
        return {
            "RecordedContainerId": (
                str(record_ref.pal.ContainerId)
                if record_ref.pal.ContainerId
                else None
            ),
            "RecordedSlotIndex": record_ref.pal.SlotIndex,
            "ActualContainerId": None,
            "ActualSlotIndex": record_ref.slot_index,
            "ActualLocations": [
                {
                    "StorageKey": record_ref.storage_key,
                    "SlotIndex": record_ref.slot_index,
                }
            ],
            "LocationStatus": "ok",
            "LocationAnomaly": None,
            "ContainerKind": record_ref.storage_kind,
            "ContainerLabel": (
                descriptor["ContainerLabel"] if descriptor else record_ref.storage_key
            ),
            "StorageKey": record_ref.storage_key,
            "StorageKind": record_ref.storage_kind,
        }

    def resolve_pal_location(self, pal: PalEntity | UUID | str) -> dict:
        pal_entity = pal if isinstance(pal, PalEntity) else self.get_pal(pal)
        if pal_entity is None:
            raise ValueError("Pal not found")

        recorded_container_id = (
            str(pal_entity.ContainerId) if pal_entity.ContainerId else None
        )
        recorded_slot_index = pal_entity.SlotIndex
        actual_slots = self.container_data.find_pal_slots(pal_entity.InstanceId)
        actual_locations = [
            {"ContainerId": str(container.ID), "SlotIndex": slot.inv_idx}
            for container, slot in actual_slots
        ]

        if recorded_container_id and self.container_data.get_container(pal_entity.ContainerId) is None:
            status = "unknown_container"
        elif not actual_slots:
            status = "missing"
        elif len(actual_slots) > 1:
            status = "duplicate"
        elif (
            str(actual_slots[0][0].ID) != recorded_container_id
            or actual_slots[0][1].inv_idx != recorded_slot_index
        ):
            status = "slot_mismatch"
        else:
            status = "ok"

        actual_container_id = actual_locations[0]["ContainerId"] if len(actual_locations) == 1 else None
        actual_slot_index = actual_locations[0]["SlotIndex"] if len(actual_locations) == 1 else None
        descriptor = self._container_descriptor_map().get(actual_container_id or recorded_container_id)
        messages = {
            "missing": "Pal is not present in any decoded container slot.",
            "slot_mismatch": "Pal SlotId does not match its actual container slot.",
            "duplicate": "Pal appears in multiple container slots.",
            "unknown_container": "Pal SlotId refers to an unknown container.",
        }
        return {
            "RecordedContainerId": recorded_container_id,
            "RecordedSlotIndex": recorded_slot_index,
            "ActualContainerId": actual_container_id,
            "ActualSlotIndex": actual_slot_index,
            "ActualLocations": actual_locations,
            "LocationStatus": status,
            "LocationAnomaly": messages.get(status),
            "ContainerKind": descriptor["ContainerKind"] if status == "ok" and descriptor else "anomaly",
            "ContainerLabel": descriptor["ContainerLabel"] if status == "ok" and descriptor else "Location anomaly",
        }

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
        if pal_entity.IsExpeditionPal:
            reject("Expedition Pals must be recalled in-game before moving.")

        location = self.resolve_pal_location(pal_entity)
        if location["LocationStatus"] != "ok":
            reject(
                f"Pal location is {location['LocationStatus']}; repair it before moving."
            )

        source_text = (
            f"{location['ActualContainerId']}@{location['ActualSlotIndex']}"
        )
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

        source_container = self.container_data.get_container(
            location["ActualContainerId"]
        )
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
            and str(pal_entity.group_id) != str(target_descriptor.get("GroupId"))
        ):
            reject("Cross-guild Pal movement is not supported.")

        source_slot = source_container.get_slot(pal_entity.InstanceId)
        if source_slot is None:
            reject("Source slot is unavailable.", f"source={source_text}")

        source_snapshot = source_container.snapshot_slots()
        target_snapshot = target_container.snapshot_slots()
        pal_param_snapshot = copy.deepcopy(pal_entity._pal_param)
        owner_entity_snapshot = pal_entity.owner_player_entity
        player_palbox_snapshots = {
            str(player.PlayerUId): (
                dict(player._palbox),
                dict(player._new_palbox),
            )
            for player in self.get_players()
        }
        baseworker_snapshot = dict(self.baseworker_mapping)
        registry_snapshot = getattr(self, "_container_registry_cache", None)

        try:
            target_slot_index = target_container.add_slot_copy(source_slot)
            if target_slot_index == -1:
                raise ValueError("Target container has no free slot.")
            source_container.del_pal(pal_entity.InstanceId)
            if source_container.has_pal(pal_entity.InstanceId):
                raise RuntimeError("Failed removing the source slot.")
            pal_entity.SlotId = (target_container.ID, target_slot_index)

            pal_key = str(pal_entity.InstanceId)
            old_owner_id = (
                str(pal_entity.OwnerPlayerUId) if pal_entity.OwnerPlayerUId else None
            )
            target_owner_id = target_descriptor.get("OwnerPlayerUId")
            if target_descriptor["ContainerKind"] == "base":
                if old_owner_id:
                    old_owner = self.get_player(old_owner_id)
                    if old_owner:
                        old_owner.pop_pal(pal_key)
                pal_entity.set_owner_player_uid(None)
                self.baseworker_mapping[pal_key] = pal_entity
            elif target_is_shared:
                self.baseworker_mapping.pop(pal_key, None)
            else:
                target_owner = self.get_player(target_owner_id)
                if target_owner is None:
                    raise ValueError("Target container owner is unavailable.")
                if old_owner_id and old_owner_id != str(target_owner.PlayerUId):
                    old_owner = self.get_player(old_owner_id)
                    if old_owner:
                        old_owner.pop_pal(pal_key)
                self.baseworker_mapping.pop(pal_key, None)
                if target_owner.get_pal(pal_key, disable_warning=True) is None:
                    if not target_owner.add_pal(pal_entity):
                        raise RuntimeError("Failed updating the target player's Pal list.")
                pal_entity.set_owner_player_uid(target_owner.PlayerUId, target_owner)

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
            pal_entity._pal_param.clear()
            pal_entity._pal_param.update(pal_param_snapshot)
            pal_entity.owner_player_entity = owner_entity_snapshot
            for player in self.get_players():
                palbox, new_palbox = player_palbox_snapshots[str(player.PlayerUId)]
                player._palbox.clear()
                player._palbox.update(palbox)
                player._new_palbox.clear()
                player._new_palbox.update(new_palbox)
            self.baseworker_mapping.clear()
            self.baseworker_mapping.update(baseworker_snapshot)
            self._container_registry_cache = registry_snapshot
            LOGGER.error(
                f"Move Pal rolled back: pal={pal_entity.InstanceId} "
                f"source={source_text} target={target_container.ID} "
                f"owner={pal_entity.OwnerPlayerUId}; error={error}\n"
                f"{traceback.format_exc()}"
            )
            raise
    
    def delete_pal(self, guid: str | UUID) -> bool:
        guid = str(guid)
        popped_pal = None
        if guid in self.baseworker_mapping:
            popped_pal = self.baseworker_mapping.pop(guid)
        elif guid in self._dangling_pals:
            popped_pal = self._dangling_pals.pop(guid)
        else:
            for player in self.get_players():
                if popped_pal := player.pop_pal(guid):
                    break
        if not popped_pal:
            LOGGER.warning(f"Can't find pal {guid}")
            return False
        try:
            if pal_group := self.group_data.get_group(popped_pal.group_id):
                pal_group.del_pal(popped_pal.InstanceId)
            if (
                pal_container := self.container_data.get_container(popped_pal.ContainerId)
            ) is not None:
                pal_container.del_pal(popped_pal.InstanceId)
            self._entities_list.remove(popped_pal._pal_obj)
        except:
            LOGGER.warning(f"Error Deleting PAL {guid}: {traceback.format_exc()}")
            return False
        self._container_registry_cache = None
        LOGGER.info(f"DELETED PAL {guid}")
        return True
    
    def heal_all_pals(self):
        for pal in self.baseworker_mapping.values():
            pal.heal_pal()
        for pal in self._dangling_pals.values():
            pal.heal_pal()
        for player in self.get_players():
            for pal in player._palbox.values():
                pal.heal_pal() 
    
    def add_pal(
        self,
        player_uid: str | UUID,
        pal_obj: dict = None,
        target_container_id: str | UUID = None,
    ) -> Optional[PalEntity]:
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
            if pal_container is None or pal_container.get_empty_slot() == -1:
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
                    and container.get_empty_slot() != -1
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

        pal_instanceId = toUUID(str(uuid.uuid4()))

        while pal_container.has_pal(pal_instanceId) or group.has_pal(pal_instanceId):
            pal_instanceId = toUUID(str(uuid.uuid4()))

        container_id = pal_container.ID
        container_added = group_added = player_added = False
        try:
            slot_idx = pal_container.add_pal(pal_instanceId)
            if slot_idx == -1:
                return None
            container_added = True
            if not pal_obj:
                pal_obj = PalObjects.PalSaveParameter(
                    pal_instanceId,
                    historical_player.PlayerUId,
                    container_id,
                    slot_idx,
                    group_id,
                )
                pal_entity = PalEntity(pal_obj)
            else:
                pal_obj = copy.deepcopy(pal_obj)
                pal_entity = PalEntity(pal_obj)
                pal_entity.InstanceId = pal_instanceId
                pal_entity.SlotId = (container_id, slot_idx)
                # I don't know why some captured pals have PlayerUId, 
                # But having non-empty ID will cause the game to hide the duped pal
                pal_entity.PlayerUId = PalObjects.EMPTY_UUID
                pal_entity.group_id = group_id
                # It seems the item container id is not necessarily referenced in the ItemContainerSaveData
                # so just assign a randomly for now.
                pal_entity._pal_param["EquipItemContainerId"] = (
                    PalObjects.PalContainerId(str(uuid.uuid4()))
                )

            historical_uid = historical_player.PlayerUId
            pal_entity._pal_param["OldOwnerPlayerUIds"] = PalObjects.ArrayProperty(
                "StructProperty",
                {
                    "prop_name": "OldOwnerPlayerUIds",
                    "prop_type": "StructProperty",
                    "values": [toUUID(historical_uid)],
                    "type_name": "Guid",
                    "id": PalObjects.EMPTY_UUID,
                },
            )
            pal_entity._pal_param["LastNickNameModifierPlayerUid"] = (
                PalObjects.Guid(historical_uid)
            )
            if owner_player is None:
                pal_entity.set_owner_player_uid(None)
            else:
                pal_entity.set_owner_player_uid(owner_player.PlayerUId, owner_player)
            pal_entity._pal_param.pop(
                "MapObjectConcreteInstanceIdAssignedToExpedition", None
            )

            pal_entity.is_new_pal = True

            if not group.add_pal(pal_instanceId):
                raise ValueError("Duplicated Pal ID in group")
            group_added = True
            if owner_player is None:
                if not hasattr(self, "baseworker_mapping"):
                    self.baseworker_mapping = {}
                self.baseworker_mapping[str(pal_instanceId)] = pal_entity
            else:
                if not owner_player.add_pal(pal_entity):
                    raise ValueError("Duplicated Pal ID, Try Again!")
                player_added = True
            self._entities_list.append(pal_obj)
        except Exception:
            if player_added:
                owner_player.pop_pal(str(pal_instanceId))
            elif owner_player is None and hasattr(self, "baseworker_mapping"):
                self.baseworker_mapping.pop(str(pal_instanceId), None)
            if group_added:
                group.del_pal(pal_instanceId)
            if container_added:
                pal_container.del_pal(pal_instanceId)
            LOGGER.error(f"Failed adding pal: {traceback.format_exc()}")
            return None
        self._container_registry_cache = None
        LOGGER.info(f"Added Pal {pal_entity} to container {pal_container.ID}")
        return pal_entity
