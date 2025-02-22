from typing import Any, Optional
from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.utils import LOGGER, alphanumeric_key
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, StatusName
from palworld_pal_editor.utils.data_provider import DataProvider
from palworld_pal_editor.utils.util import clamp, type_guard


class PlayerEntity:
    MAX_LEVEL = 60
    MAX_INVALID_LEVEL = 100

    def __init__(
        self,
        group_id: UUID | str,
        player_obj: dict,
        palbox: dict[str, PalEntity],
        gvas_file: GvasFile,
        compression_times: int,
    ) -> None:
        self._player_obj: dict = player_obj
        self._palbox: dict[str, PalEntity] = palbox
        self._new_palbox: dict[str, PalEntity] = {}
        self._gvas_file: GvasFile = gvas_file
        self._gvas_compression_times: int = compression_times
        self.group_id = group_id

        if (
            self._player_obj["value"]["RawData"]["value"]["object"]["SaveParameter"][
                "struct_type"
            ]
            != "PalIndividualCharacterSaveParameter"
        ):
            raise Exception(
                f"{self._player_obj}'s save param is not PalIndividualCharacterSaveParameter"
            )

        self._player_key: dict = self._player_obj["key"]
        self._player_param: dict = self._player_obj["value"]["RawData"]["value"][
            "object"
        ]["SaveParameter"]["value"]
        if not PalObjects.get_BaseType(self._player_param.get("IsPlayer")):
            raise TypeError(
                "Expecting player_obj, received pal_obj: {} - {} - {} - {}".format(
                    PalObjects.get_BaseType(self._player_param.get("CharacterID")),
                    self.NickName,
                    self.PlayerUId,
                    self.InstanceId,
                )
            )

        self._player_save_data: dict = self._gvas_file.properties["SaveData"]["value"]

        IndividualId = self._player_save_data.get("IndividualId", {}).get("value", {})
        sav_playerUId = PalObjects.get_BaseType(IndividualId.get("PlayerUId"))
        sav_InstanceId = PalObjects.get_BaseType(IndividualId.get("InstanceId"))
        if self.PlayerUId != sav_playerUId:
            raise Exception(
                f"PlayerUId unmatch: Level.sav: {self.PlayerUId} v.s. playerid.sav {sav_playerUId}"
            )
        if self.InstanceId != sav_InstanceId:
            raise Exception(
                f"InstanceId unmatch: Level.sav: {self.InstanceId} v.s. playerid.sav {sav_InstanceId}"
            )
        

    def __str__(self) -> str:
        return "{} - {} - {}".format(self.NickName, self.PlayerUId, self.InstanceId)

    def __hash__(self) -> int:
        return hash((self.InstanceId.__hash__(), self.PlayerUId.__hash__()))

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, PlayerEntity)
            and self.InstanceId == __value.InstanceId
            and self.PlayerUId == __value.PlayerUId
        )

    @property
    def PlayerUId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._player_key.get("PlayerUId"))

    @property
    def InstanceId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._player_key.get("InstanceId"))

    @property
    def NickName(self) -> Optional[str]:
        return PalObjects.get_BaseType(self._player_param.get("NickName"))
    
    @NickName.setter
    @LOGGER.change_logger("NickName")
    @type_guard
    def NickName(self, value: str) -> None:
        if self.NickName is None:
            self._player_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self._player_param["NickName"]["value"] = value

        if not self.NickName:
            self._player_param.pop("NickName", None)

    @property
    def UnusedStatusPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_param.get("UnusedStatusPoint"))
    
    @UnusedStatusPoint.setter
    @LOGGER.change_logger("UnusedStatusPoint")
    @type_guard
    def UnusedStatusPoint(self, value: int) -> None:
        value = clamp(PalObjects.UInt16Min, PalObjects.UInt16Max, value)
        if self.UnusedStatusPoint is None:
            self._player_param["UnusedStatusPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_param["UnusedStatusPoint"], value)

    @property
    def GotStatusPointList(self) -> Optional[list[dict]]:
        return PalObjects.get_ArrayProperty(self._player_param.get("GotStatusPointList"))
    
    @property
    def GotExStatusPointList(self) -> Optional[list[dict]]:
        return PalObjects.get_ArrayProperty(self._player_param.get("GotExStatusPointList"))
    
    @property
    def StatusPointHP(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxHP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointSP(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxSP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointATK(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.Attack):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointCarryWeight(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CarryWeight):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointCaptureRate(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CaptureRate):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointWorkSpeed(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.WorkSpeed):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    # do this for ex points as well, while ex points do not have the capture rate thing
    @property
    def ExStatusPointHP(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxHP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointSP(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxSP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
    
    @property
    def ExStatusPointATK(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()
        
        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.Attack):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointCarryWeight(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CarryWeight):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointWorkSpeed(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.WorkSpeed):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point

    @property
    def Level(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self._player_param.get("Level"))
    
    @Level.setter
    @LOGGER.change_logger("Level")
    @type_guard
    def Level(self, value: int) -> None:
        value = clamp(1, PlayerEntity.MAX_INVALID_LEVEL, value)
        if self.Level is None:
            self._player_param["Level"] = PalObjects.ByteProperty(1)
        
        status_points = value - self.Level
        new_unused_status_point = (self.UnusedStatusPoint or 0) + status_points
        if new_unused_status_point < 0:
            LOGGER.warning(f"Player {self} has insufficient status points to level down.")
            return
        
        PalObjects.set_ByteProperty(self._player_param["Level"], value)
        self.Exp = DataProvider.get_player_level_xp(self.Level)
        self.UnusedStatusPoint = new_unused_status_point
    
    @property
    def Exp(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_param.get("Exp"))
    
    @Exp.setter
    @LOGGER.change_logger("Exp")
    @type_guard
    def Exp(self, value: int) -> None:
        if self.Exp is None:
            self._player_param["Exp"] = PalObjects.Int64Property(value)
        else:
            PalObjects.set_BaseType(self._player_param["Exp"], value)

    @property
    def OtomoCharacterContainerId(self) -> Optional[UUID]:
        return PalObjects.get_PalContainerId(
            self._player_save_data.get("OtomoCharacterContainerId")
        )

    @property
    def PalStorageContainerId(self) -> Optional[UUID]:
        return PalObjects.get_PalContainerId(
            self._player_save_data.get("PalStorageContainerId")
        )

    @property
    def OtomoOrder(self) -> Optional[str]:
        # what is this thing??
        return PalObjects.get_EnumProperty(self._player_save_data.get("OtomoOrder"))

    @property
    def UnlockedRecipeTechnologyNames(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(
            self._player_save_data.get("UnlockedRecipeTechnologyNames")
        )

    @LOGGER.change_logger("UnlockedRecipeTechnologyNames")
    def toggle_UnlockedRecipeTechnologyNames(self, tech: str, status: bool):
        if self.UnlockedRecipeTechnologyNames is None:
            self._player_save_data["UnlockedRecipeTechnologyNames"] = (
                PalObjects.ArrayProperty("NameProperty", {"values": []})
            )
        if status:
            if tech in self.UnlockedRecipeTechnologyNames:
                LOGGER.warning(f"Attempt to unlock {self}, but it has already been unlocked, skipping")
                return
            self.UnlockedRecipeTechnologyNames.append(tech)
        else:
            if tech not in self.UnlockedRecipeTechnologyNames:
                LOGGER.warning(f"Attempt to lock {self}, but it has not been unlocked, skipping")
                return
            self.UnlockedRecipeTechnologyNames.remove(tech)

    def has_viewing_cage(self) -> bool:
        if not self.UnlockedRecipeTechnologyNames:
            return False
        return "DisplayCharacter" in self.UnlockedRecipeTechnologyNames

    def unlock_viewing_cage(self):
        self.toggle_UnlockedRecipeTechnologyNames("DisplayCharacter", True)

    @property
    def PlayerGVAS(self) -> Optional[tuple[GvasFile, int]]:
        if (self._gvas_file is None) or (self._gvas_compression_times is None):
            return None
        return self._gvas_file, self._gvas_compression_times

    def add_pal(self, pal_entity: PalEntity) -> bool:
        """
        This method only inserts player's pals to `self.palbox`.\n
        """
        pal_guid = str(pal_entity.InstanceId)
        if pal_guid in self._palbox:
            return False
        
        if pal_entity.is_new_pal:
            self._new_palbox[pal_guid] = pal_entity

        self._palbox[pal_guid] = pal_entity
        pal_entity.set_owner_player_entity(self)
        return True
    
    @property
    def TechnologPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_save_data.get("TechnologPoint"))
    
    @TechnologPoint.setter
    @LOGGER.change_logger("TechnologPoint")
    @type_guard
    def TechnologPoint(self, value: int) -> None:
        if self.TechnologPoint is None:
            self._player_save_data["TechnologPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_save_data["TechnologPoint"], value)

    @property
    def bossTechPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_save_data.get("bossTechPoint"))
    
    @bossTechPoint.setter
    @LOGGER.change_logger("bossTechPoint")
    @type_guard
    def bossTechPoint(self, value: int) -> None:
        if self.bossTechPoint is None:
            self._player_save_data["bossTechPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_save_data["bossTechPoint"], value)
    
    def try_create_pal_record_data(self):
        if "RecordData" not in self._player_save_data:
            self._player_save_data["RecordData"] = PalObjects.PalLoggedinPlayerSaveDataRecordData()
        record_data = self._player_save_data["RecordData"]["value"]

        if "PalCaptureCount" not in record_data:
            record_data["PalCaptureCount"] = PalObjects.MapProperty("NameProperty", "IntProperty")
        
        if "PaldeckUnlockFlag" not in record_data:
            record_data["PaldeckUnlockFlag"] = PalObjects.MapProperty("NameProperty", "BoolProperty")

    @property
    def PalCaptureCount(self) -> Optional[list]:
        if not (record_data := self._player_save_data.get("RecordData", None)):
            return None
        record_data: dict = record_data["value"]
        return PalObjects.get_MapProperty(record_data.get("PalCaptureCount", None))
    
    @property
    def PaldeckUnlockFlag(self) -> Optional[list]:
        if not (record_data := self._player_save_data.get("RecordData", None)):
            return None
        record_data: dict = record_data["value"]
        return PalObjects.get_MapProperty(record_data.get("PaldeckUnlockFlag", None))

    def get_pal_capture_count(self, name: str) -> int:
        try:
            return self._player_save_data["RecordData"]["value"]["PalCaptureCount"]["value"][name]
        except:
            return 0
        
    def inc_pal_capture_count(self, name: str):
        self.try_create_pal_record_data()
        for record in self.PalCaptureCount:
            if record['key'].lower() == name.lower():
                record['value'] += 1
                return
        LOGGER.info(f"Creating new pal capture count record for {name}")
        self.PalCaptureCount.append({
            'key': name,
            'value': 1
        })

    def unlock_paldeck(self, name: str):
        self.try_create_pal_record_data()
        for record in self.PaldeckUnlockFlag:
            if record['key'].lower() == name.lower():
                record['value'] = True
                return
        self.PaldeckUnlockFlag.append({
            'key': name,
            'value': True
        })

    def save_new_pal_records(self):
        """
        This should only be called on save
        """
        def handle_special_keys(key) -> str:
            match key:
                case 'PlantSlime_Flower': return 'PlantSlime'
                case 'SheepBall': return 'Sheepball'
                case 'LazyCatFish': return 'LazyCatfish'
                case 'Blueplatypus': return 'BluePlatypus'
            return key
        
        for guid in self._new_palbox:
            pal_entity = self._new_palbox[guid]
            if DataProvider.is_pal_invalid(pal_entity.DataAccessKey):
                LOGGER.info(f"Skip player records update for invalid pal: {pal_entity}")
                continue
            if pal_entity.IsHuman or not DataProvider.get_pal_sorting_key(pal_entity.DataAccessKey):
                LOGGER.info(f"Skip player records update for pal: {pal_entity}")
                continue

            key = handle_special_keys(pal_entity.RawSpecieKey)
            self.unlock_paldeck(key)
            self.inc_pal_capture_count(key)

            tech_key = "SkillUnlock_" + key
            if DataProvider.get_tech_i18n(tech_key) is None:
                LOGGER.warning(f"Technology {tech_key} not found, please report this to the dev.")
            else:
                self.toggle_UnlockedRecipeTechnologyNames(tech_key, True)

            pal_entity.is_new_pal = False

        self._new_palbox.clear()

    def get_pals(self) -> list[PalEntity]:
        return self._palbox.values()

    def pop_pal(self, guid: str | UUID) -> Optional[PalEntity]:
        if guid in self._new_palbox:
            self._new_palbox.pop(guid)
        return self._palbox.pop(guid, None)

    def get_pal(self, guid: UUID | str, disable_warning=False) -> Optional[PalEntity]:
        guid = str(guid)
        if guid in self._palbox:
            return self._palbox[guid]
        
        if not disable_warning:
            LOGGER.warning(f"Player {self} has no pal {guid}.")

    def get_sorted_pals(self, sorting_key="paldeck") -> list[PalEntity]:
        match sorting_key:
            case "paldeck":
                return sorted(
                    self.get_pals(),
                    key=lambda pal: (
                        pal.IsHuman or False,
                        alphanumeric_key(pal.PalDeckID),
                        pal.IsTower,
                        pal.IsBOSS,
                        pal.IsRarePal or False,
                        pal.Level or 1,
                    ),
                )
