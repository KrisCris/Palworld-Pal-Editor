from typing import Any, Optional
from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.utils import LOGGER, alphanumeric_key
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, get_attr_value


class PlayerEntity:
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

        if not get_attr_value(self._player_param, "IsPlayer"):
            raise TypeError(
                "Expecting player_obj, received pal_obj: {} - {} - {} - {}".format(
                    get_attr_value(self._player_param, "CharacterID"),
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
        return get_attr_value(self._player_key, "PlayerUId")

    @property
    def InstanceId(self) -> Optional[UUID]:
        return get_attr_value(self._player_key, "InstanceId")

    @property
    def NickName(self) -> Optional[str]:
        return get_attr_value(self._player_param, "NickName")

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

    def add_UnlockedRecipeTechnologyNames(self, tech: str) -> bool:
        if self.UnlockedRecipeTechnologyNames is None:
            self._player_save_data["UnlockedRecipeTechnologyNames"] = (
                PalObjects.ArrayProperty("NameProperty", {"values": []})
            )

        if tech in self.UnlockedRecipeTechnologyNames:
            LOGGER.warning(f"{self} has already been unlocked, skipping")
            return False

        self.UnlockedRecipeTechnologyNames.append(tech)

    def has_viewing_cage(self) -> bool:
        if not self.UnlockedRecipeTechnologyNames:
            return False
        return "DisplayCharacter" in self.UnlockedRecipeTechnologyNames

    def unlock_viewing_cage(self):
        self.add_UnlockedRecipeTechnologyNames("DisplayCharacter")

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
        self._palbox[pal_guid] = pal_entity
        pal_entity.set_owner_player_entity(self)
        return True

    def get_pals(self) -> list[PalEntity]:
        return self._palbox.values()

    def pop_pal(self, guid: str | UUID) -> Optional[PalEntity]:
        return self._palbox.pop(guid, None)

    def get_pal(self, guid: UUID | str) -> Optional[PalEntity]:
        guid = str(guid)
        if guid in self._palbox:
            return self._palbox[guid]
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
