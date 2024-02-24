import logging
import json
import uuid
import math
import copy
from pathlib import Path
from typing import Optional

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import FArchiveReader, FArchiveWriter, UUID
from palworld_save_tools.json_tools import CustomEncoder
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES, PALWORLD_TYPE_HINTS

from .pal_objects import get_attr_value, toUUID
from .player_entity import PlayerEntity
from .pal_entity import PalEntity
from .utils import Logger

LOGGER = Logger()


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


PALEDITOR_CUSTOM_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSaveData"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.FoliageGridSaveDataMap"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSpawnerInStageSaveData"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.DynamicItemSaveData"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.ItemContainerSaveData"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.CharacterContainerSaveData"] = (skip_decode, skip_encode)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.GroupSaveDataMap"] = (skip_decode, skip_encode)


class SaveManager:
    # Although these are class attrs, SaveManager itself is singleton.
    _instance = None
    _file_path: Optional[Path]
    _raw_gvas: Optional[bytes]
    _compression_times: Optional[int]

    gvas_file: Optional[GvasFile]
    entities_list: Optional[list[dict]]
    player_mapping: Optional[dict[str, PlayerEntity]]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            # self._file_path: Optional[Path] = None
            # self._raw_gvas: Optional[bytes] = None
            # self._compression_times: Optional[int] = None
            # self.gvas_file: Optional[GvasFile] = None
            # self.entities_list: Optional[list[dict]] = None
            # self.player_list: Optional[list[PlayerEntity]] = None

    def list_players(self) -> list[PlayerEntity]:
        player_list = []
        for player in self.player_mapping.values():
            LOGGER.info(player)
            player_list.append(player)
        return player_list
    
    def get_player(self, guid: UUID | str) -> Optional[PlayerEntity]:
        guid = str(guid)
        if guid in self.player_mapping:
            player = self.player_mapping[guid]
            LOGGER.info(player)
            return player
        LOGGER.warning(f"Player {guid} not exist")

    def _load_entities(self):
        self.player_mapping = {}
        temp_player_pal_mapping: dict[str, dict[str, PalEntity]] = {}
        for entity in self.entities_list:
            entity_struct = entity["value"]["RawData"]["value"]["object"]["SaveParameter"]
            if entity_struct['struct_type'] != 'PalIndividualCharacterSaveParameter':
                LOGGER.warning(f"Non-player/pal data found in CharacterSaveParameterMap, skipping {entity}")
                continue

            entity_param = entity_struct['value']
            try: 
                if get_attr_value(entity_param, "IsPlayer"):
                    uid_str = str(get_attr_value(entity['key'], "PlayerUId"))

                    if uid_str in temp_player_pal_mapping:
                        player_entity = PlayerEntity(entity, temp_player_pal_mapping[uid_str])
                        del temp_player_pal_mapping[uid_str]
                    else:
                        player_entity = PlayerEntity(entity, dict())

                    if uid_str in self.player_mapping:
                        LOGGER.error("Duplicated player found: \n\t%s\n\t%s\n\tskipping" % 
                                       (self.player_mapping[uid_str], player_entity))
                        continue
                
                    self.player_mapping[uid_str] = player_entity
                    LOGGER.info("Found player: %s" % str(player_entity))
                else:
                    pal_entity = PalEntity(entity)
                    owner = pal_entity.OwnerPlayerUId
                    if owner:
                        owner_str = str(owner)
                        if owner_str in self.player_mapping:
                            self.player_mapping[owner_str].add_pal(pal_entity)
                        else:
                            temp_player_pal_mapping.setdefault(owner_str, dict())[pal_entity.InstanceId] = pal_entity
                        LOGGER.info("Found pal: %s" % str(pal_entity))

                    else:
                        LOGGER.error("Found dangling pal object: %s, skipping", str(pal_entity))
                        continue

            except Exception as e:
                LOGGER.error("Error occured while init'in object: %s, skipping" % e)
                continue
        
        for player_str_uid in self.player_mapping:
            player = self.player_mapping[player_str_uid]
            LOGGER.nextline()
            LOGGER.info("%s" % (player))
            for pal in player.palbox.values():
                LOGGER.info("\t%s" % (pal))

        for uid_str in temp_player_pal_mapping:
            pal_list = temp_player_pal_mapping[uid_str]
            LOGGER.nextline()
            LOGGER.warning(f"Dangling pals found of non-existing user {uid_str}")
            for pal in pal_list.values():
                LOGGER.warning("\t%s", str(pal))
                
    def open(self, file_path: str) -> Optional[GvasFile]:
        self._file_path = Path(file_path).resolve()
        if not self._file_path.exists():
            LOGGER.error(f"Save file does not exist: {self._file_path}.")
            return None

        LOGGER.info(f"Opening {self._file_path}")
        with self._file_path.open("rb") as file:
            data = file.read()

            try:
                LOGGER.info("Decompressing sav")
                self._raw_gvas, self._compression_times = decompress_sav_to_gvas(data)
            except Exception as e:
                LOGGER.error(f"Caught Exception: palworld_save_tools::palsav::decompress_sav_to_gvas: {e}")
                return None
            
            LOGGER.info("Reading GVAS file")
            self.gvas_file = GvasFile.read(
                self._raw_gvas, PALWORLD_TYPE_HINTS, PALEDITOR_CUSTOM_PROPERTIES
            )

            try:
                self.entities_list = self.gvas_file.properties["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]
            except Exception as e:
                LOGGER.error(f"Unable to retrieve pal data: {e}")
                return None

            self._load_entities()

            LOGGER.info("Done")
        return self.gvas_file

    def save(self, file_path: str, _create_dir=False) -> bool:
        if self.gvas_file is None:
            LOGGER.error("No gvas_file stored in save manager, aborting")
            return False
        if self._compression_times is None:
            LOGGER.warning("_compression_times is None, aborting")
            return False

        output_path = Path(file_path).resolve()

        if not output_path.parent.exists():
            LOGGER.error(f"Path does not exist: {output_path.parent}")
            if _create_dir:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                LOGGER.debug(f"Path {output_path.parent} created")
            else:
                return False

        LOGGER.info("Compressing GVAS file")
        sav_data = compress_gvas_to_sav(
            self.gvas_file.write(PALEDITOR_CUSTOM_PROPERTIES), self._compression_times
        )

        LOGGER.info(f"Saving to {output_path}")
        with output_path.open("wb") as file:
            file.write(sav_data)
        LOGGER.info(f"Saved to {output_path}")
        return True