from enum import Enum
import json
from typing import Any, Optional
import uuid
from palworld_save_tools.archive import UUID
from palworld_save_tools.json_tools import CustomEncoder

from palworld_pal_editor.utils import LOGGER, clamp


def dumps(data: dict) -> str:
    return json.dumps(data, indent=4, cls=CustomEncoder, ensure_ascii=False)


def isUUIDStr(uuid_str: str) -> Optional[UUID]:
    try:
        uuid = UUID.from_str(str(uuid_str))
        if str(uuid) == uuid_str.lower():
            return uuid
        raise Exception(f"{uuid_str} is not a valid UUID")
    except Exception:
        LOGGER.warning("isUUIDStr: {e}")
        return None


def toUUID(uuid_str: str) -> Optional[UUID]:
    if isinstance(uuid_str, UUID):
        return uuid_str
    return isUUIDStr(uuid_str)


def UUID2HexStr(uuid: str | UUID) -> str:
    return str(uuid).upper().replace("-", "")


def get_nested_attr(container: dict, keys: list) -> Optional[Any]:
    """
    Retrieve a value from a nested dictionary using a sequence of keys.

    :param container: The dictionary to search through.
    :param keys: A tuple of keys representing the path to the desired value.
    :return: The value found at the end of the keys path, or None if any key is missing.
    """
    current_level = container
    for key in keys:
        try:
            current_level = current_level[key]
        except Exception as e:
            # LOGGER.warning(e)
            return None
    return current_level


class PalGender(Enum):
    MALE = "EPalGenderType::Male"
    FEMALE = "EPalGenderType::Female"

    @staticmethod
    def from_value(value: str):
        if value is None:
            return None
        try:
            return PalGender(value)
        except:
            LOGGER.warning(f"{value} is not a valid PalGender")


class PalSuitability(Enum):
    EmitFlame = "EPalWorkSuitability::EmitFlame"
    Watering = "EPalWorkSuitability::Watering"
    Seeding = "EPalWorkSuitability::Seeding"
    GenerateElectricity = "EPalWorkSuitability::GenerateElectricity"
    Handcraft = "EPalWorkSuitability::Handcraft"
    Collection = "EPalWorkSuitability::Collection"
    Deforest = "EPalWorkSuitability::Deforest"
    Mining = "EPalWorkSuitability::Mining"
    OilExtraction = "EPalWorkSuitability::OilExtraction"
    ProductMedicine = "EPalWorkSuitability::ProductMedicine"
    Cool = "EPalWorkSuitability::Cool"
    Transport = "EPalWorkSuitability::Transport"
    MonsterFarm = "EPalWorkSuitability::MonsterFarm"

    @staticmethod
    def from_value(value: str):
        if value is None:
            return None
        try:
            return PalSuitability(value)
        except:
            LOGGER.warning(f"{value} is not a valid PalSuitability")

class StatusName():
    MaxHP = "最大HP"
    MaxSP = "最大SP"
    Attack = "攻撃力"
    CarryWeight = "所持重量"
    CaptureRate = "捕獲率"
    WorkSpeed = "作業速度"

class PalObjects:
    EMPTY_UUID = toUUID("00000000-0000-0000-0000-000000000000")
    TIME = 638486453957560000

    UInt16Max = 65535
    UInt16Min = 0

    @staticmethod
    def StrProperty(value: str):
        return {"id": None, "type": "StrProperty", "value": value}

    @staticmethod
    def NameProperty(value: str):
        return {"id": None, "type": "NameProperty", "value": value}

    @staticmethod
    def IntProperty(value: int):
        return {"id": None, "type": "IntProperty", "value": value}

    @staticmethod
    def Int64Property(value: int):
        return {"id": None, "type": "Int64Property", "value": value}

    @staticmethod
    def FloatProperty(value: float):
        return {"id": None, "type": "FloatProperty", "value": value}

    @staticmethod
    def BoolProperty(value: bool):
        return {"value": value, "id": None, "type": "BoolProperty"}

    @staticmethod
    def ByteProperty(value: Any, type: str = "None"):
        return {
            "value": {"type": type, "value": value},
            "id": None,
            "type": "ByteProperty",
        }

    @staticmethod
    def get_BaseType(container: dict) -> Optional[Any]:
        return get_nested_attr(container, ["value"])

    @staticmethod
    def set_BaseType(container: dict, value: Any):
        container["value"] = value

    @staticmethod
    def get_ByteProperty(container: dict) -> Optional[Any]:
        return get_nested_attr(container, ["value", "value"])

    @staticmethod
    def set_ByteProperty(container: dict, value: Any):
        container["value"]["value"] = value

    @staticmethod
    def Guid(value: str | UUID):
        return {
            "struct_type": "Guid",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": toUUID(value),
            "type": "StructProperty",
        }

    @staticmethod
    def EnumProperty(type: str, value: Enum | str):
        """
        Example:
        >>> "Gender":{
                "id":None,
                "value": {
                    "type":"EPalGenderType",
                    "value":"EPalGenderType::Female"
                },
                "type":"EnumProperty"
            },
        """

        return {
            "id": None,
            "type": "EnumProperty",
            "value": {
                "type": type,
                "value": value.value if isinstance(value, Enum) else value,
            },
        }

    @staticmethod
    def get_EnumProperty(container: dict) -> Optional[str]:
        return get_nested_attr(container, ["value", "value"])

    @staticmethod
    def set_EnumProperty(container: dict, value: str):
        container["value"]["value"] = value

    @staticmethod
    def ArrayProperty(array_type: str, value: dict, custom_type: Optional[str] = None):
        """
        Example:
        >>> "RawData":{
                "array_type":"ByteProperty",
                "id":None,
                "value":{...},
                "type":"ArrayProperty",
                "custom_type":".worldSaveData.CharacterSaveParameterMap.Value.RawData"
            }

        >>> "EquipWaza":{
                "array_type":"EnumProperty",
                "id":None,
                "value":{
                    "values":[
                        "EPalWazaID::DarkBall",
                        "EPalWazaID::DarkWave",
                        "EPalWazaID::SandTornado"
                    ]
                },
                "type":"ArrayProperty"
            },

        >>> "PassiveSkillList":{
                "array_type":"NameProperty",
                "id":None,
                "value":{
                    "values":[
                        "TrainerATK_UP_1",
                        "MoveSpeed_up_2",
                        "ElementBoost_Ice_1_PAL"
                    ]
                },
                "type":"ArrayProperty"
            },
        """

        struct = {
            "array_type": array_type,
            "id": None,
            "value": value,
            "type": "ArrayProperty",
        }

        if custom_type:
            struct["custom_type"] = custom_type

        return struct

    @staticmethod
    def get_ArrayProperty(container: dict) -> Optional[list[Any]]:
        """
        Please note that custom_type is unsupported!
        """
        return get_nested_attr(container, ["value", "values"])

    @staticmethod
    def add_ArrayProperty(container: dict, value: Any):
        PalObjects.get_ArrayProperty(container).append(value)

    @staticmethod
    def pop_ArrayProperty(container: dict, index: Any) -> Any:
        return PalObjects.get_ArrayProperty(container).pop(index)

    @staticmethod
    def FixedPoint64(value: int):
        """
        Example:
        >>> "HP":{
            "struct_type":"FixedPoint64",
            "struct_id":"00000000-0000-0000-0000-000000000000",
            "id":None,
            "value":{
                "Value":{
                    "id":None,
                    "value":1690000,
                    "type":"Int64Property"
                }
            },
            "type":"StructProperty"
        },
        """
        return {
            "struct_type": "FixedPoint64",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {"Value": PalObjects.Int64Property(value)},
            "type": "StructProperty",
        }

    @staticmethod
    def get_FixedPoint64(container: dict) -> Optional[int]:
        int64: Optional[dict] = get_nested_attr(container, ["value", "Value"])
        return PalObjects.get_BaseType(int64)

    @staticmethod
    def set_FixedPoint64(container: dict, value: int):
        PalObjects.set_BaseType(container["value"]["Value"], value)

    @staticmethod
    def PalContainerId(id: UUID | str):
        return {
            "struct_type": "PalContainerId",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {"ID": PalObjects.Guid(id)},
            "type": "StructProperty",
        }

    @staticmethod
    def get_PalContainerId(container: dict) -> Optional[UUID]:
        return PalObjects.get_BaseType(get_nested_attr(container, ["value", "ID"]))

    @staticmethod
    def set_PalContainerId(container: dict, id: str | UUID):
        id = toUUID(id)
        PalObjects.set_BaseType(container["value"]["ID"], id)

    @staticmethod
    def PalCharacterSlotId(slot: int, id: UUID | str):
        return {
            "struct_type": "PalCharacterSlotId",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {
                "ContainerId": PalObjects.PalContainerId(id),
                "SlotIndex": PalObjects.IntProperty(slot),
            },
            "type": "StructProperty",
        }

    @staticmethod
    def get_PalCharacterSlotId(container: dict) -> Optional[tuple[UUID, int]]:
        container_id = PalObjects.get_PalContainerId(
            get_nested_attr(container, ["value", "ContainerId"])
        )
        slot_idx = PalObjects.get_BaseType(
            get_nested_attr(container, ["value", "SlotIndex"])
        )
        if container_id is None or slot_idx is None:
            return None
        return (container_id, slot_idx)

    @staticmethod
    def set_PalCharacterSlotId(
        container: dict, container_id: UUID | str, slot_idx: int
    ):
        PalObjects.set_PalContainerId(container["value"]["ContainerId"], container_id)
        PalObjects.set_BaseType(container["value"]["SlotIndex"], slot_idx)

    @staticmethod
    def FloatContainer(value: dict):
        return {
            "struct_type": "FloatContainer",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": value,
            "type": "StructProperty",
        }

    @staticmethod
    def ContainerSlotData(slotidx: int):
        return {
            "SlotIndex": PalObjects.IntProperty(slotidx),
            "RawData": PalObjects.ArrayProperty(
                "ByteProperty",
                {
                    "player_uid": PalObjects.EMPTY_UUID,
                    "instance_id": PalObjects.EMPTY_UUID,
                    "permission_tribe_id": 0,
                },
                ".worldSaveData.CharacterContainerSaveData.Value.Slots.Slots.RawData",
            ),
        }

    @staticmethod
    def GotWorkSuitabilityAddRankList():
        return PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "GotWorkSuitabilityAddRankList",
                "prop_type": "StructProperty",
                "values": [],
                "type_name": "PalWorkSuitabilityInfo",
                "id": "00000000-0000-0000-0000-000000000000",
            },
        )

    @staticmethod
    def WorkSuitability(suitability, rank):
        return {
            "WorkSuitability": PalObjects.EnumProperty(
                "EPalWorkSuitability", suitability
            ),
            "Rank": PalObjects.IntProperty(rank),
        }

    @staticmethod
    def get_WorkSuitabilities(
        container: dict,
    ) -> Optional[dict[PalSuitability, int]]:
        ret = {}
        suitabilities = PalObjects.get_ArrayProperty(container)
        if suitabilities is None:
            return None
        for suitability in suitabilities:
            ability = PalObjects.get_EnumProperty(suitability.get("WorkSuitability"))
            rank = PalObjects.get_BaseType(suitability.get("Rank"))
            if ability is None or rank is None:
                continue
            ret[PalSuitability.from_value(ability)] = rank
        return ret

    @staticmethod
    def set_WorkSuitability(container, suitability: str | PalSuitability, rank: int):
        if isinstance(suitability, PalSuitability):
            suitability = suitability.value
        suitabilities = PalObjects.get_ArrayProperty(container)
        # exists = False
        # to fix mistakes made by previous version
        filtered_numbers = [
            suit
            for suit in suitabilities
            if PalObjects.get_EnumProperty(suit.get("WorkSuitability")) != suitability
        ]
        suitabilities.clear()
        suitabilities.extend(filtered_numbers)
        if rank > 0:
            suitabilities.append(PalObjects.WorkSuitability(suitability, rank))
        # for idx, ability in enumerate(suitabilities):
        #     if (
        #         PalObjects.get_EnumProperty(ability.get("WorkSuitability"))
        #         == suitability
        #     ):
        #         exists = True
        #         break

        # if exists:
        #     if rank == 0:
        #         suitabilities.pop(idx)
        #     else:
        #         PalObjects.set_BaseType(ability.get("Rank"), rank)
        # elif rank != 0:
        #     suitabilities.append(PalObjects.WorkSuitability(suitability, rank))

    @staticmethod
    def pop_WorkSuitability(container, suitability: str | PalSuitability):
        if isinstance(suitability, PalSuitability):
            suitability = suitability.value
        suitabilities = PalObjects.get_ArrayProperty(container)
        for idx, ability in enumerate(suitabilities):
            if (
                PalObjects.get_EnumProperty(ability.get("WorkSuitability"))
                == suitability
            ):
                PalObjects.pop_ArrayProperty(container, idx)

    @staticmethod
    def individual_character_handle_id(instance_id: UUID | str, guid=None):
        guid = guid or PalObjects.EMPTY_UUID
        return {
            "guid": toUUID(guid),
            "instance_id": toUUID(instance_id),
        }

    @staticmethod
    def DateTime(time):
        return {
            "struct_type": "DateTime",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": time,
            "type": "StructProperty",
        }

    @staticmethod
    def Vector(x, y, z):
        return {
            "struct_type": "Vector",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {
                "x": x,
                "y": y,
                "z": z,
            },
            "type": "StructProperty",
        }

    @staticmethod
    def PalLoggedinPlayerSaveDataRecordData(value: dict = None):
        return {
            "struct_type": "PalLoggedinPlayerSaveDataRecordData",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": value or {},
            "type": "StructProperty",
        }

    @staticmethod
    def MapProperty(
        key_type: str, value_type: str, key_struct_type=None, value_struct_type=None
    ):
        return {
            "key_type": key_type,
            "value_type": value_type,
            "key_struct_type": key_struct_type,
            "value_struct_type": value_struct_type,
            "id": None,
            "value": [],
            "type": "MapProperty",
        }

    @staticmethod
    def get_MapProperty(container: dict) -> Optional[list[dict]]:
        return get_nested_attr(container, ["value"])

    StatusNames = [
        "最大HP",
        "最大SP",
        "攻撃力",
        "所持重量",
        "捕獲率",
        "作業速度",
    ]

    ExStatusNames = [
        "最大HP",
        "最大SP",
        "攻撃力",
        "所持重量",
        "作業速度",
    ]

    @staticmethod
    def StatusPointStruct(name, point):
        return {
            "StatusName": PalObjects.NameProperty(name),
            "StatusPoint": PalObjects.IntProperty(point),
        }

    @staticmethod
    def GotExStatusPointList():
        return PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "GotExStatusPointList",
                "prop_type": "StructProperty",
                "values": [
                    PalObjects.StatusPointStruct(name, 0)
                    for name in PalObjects.ExStatusNames
                ],
                "type_name": "PalGotStatusPoint",
                "id": PalObjects.EMPTY_UUID,
            },
        )
    
    @staticmethod
    def GotStatusPointList():
        return PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "GotStatusPointList",
                "prop_type": "StructProperty",
                "values": [
                    PalObjects.StatusPointStruct(name, 0)
                    for name in PalObjects.StatusNames
                ],
                "type_name": "PalGotStatusPoint",
                "id": PalObjects.EMPTY_UUID,
            },
        )

    @staticmethod
    def PalSaveParameter(InstanceId, OwnerPlayerUId, ContainerId, SlotIndex, group_id):
        return {
            "key": {
                "PlayerUId": PalObjects.Guid(PalObjects.EMPTY_UUID),
                "InstanceId": PalObjects.Guid(InstanceId),
                "DebugName": PalObjects.StrProperty(""),
            },
            "value": {
                "RawData": PalObjects.ArrayProperty(
                    "ByteProperty",
                    {
                        "object": {
                            "SaveParameter": {
                                "struct_type": "PalIndividualCharacterSaveParameter",
                                "struct_id": PalObjects.EMPTY_UUID,
                                "id": None,
                                "value": {
                                    "CharacterID": PalObjects.NameProperty("SheepBall"),
                                    "Gender": PalObjects.EnumProperty(
                                        "EPalGenderType", "EPalGenderType::Female"
                                    ),
                                    "NickName": PalObjects.StrProperty("!!!NEW PAL!!!"),
                                    "EquipWaza": PalObjects.ArrayProperty(
                                        "EnumProperty",
                                        {
                                            "values": [
                                                "EPalWazaID::Unique_SheepBall_Roll"
                                            ]
                                        },
                                    ),
                                    "MasteredWaza": PalObjects.ArrayProperty(
                                        "EnumProperty",
                                        {"values": []},
                                    ),
                                    "Hp": PalObjects.FixedPoint64(545000),
                                    "Talent_HP": PalObjects.ByteProperty(100),
                                    "Talent_Shot": PalObjects.ByteProperty(100),
                                    "Talent_Defense": PalObjects.ByteProperty(100),
                                    "FullStomach": PalObjects.FloatProperty(150.0),
                                    "PassiveSkillList": PalObjects.ArrayProperty(
                                        "NameProperty", {"values": []}
                                    ),
                                    "OwnedTime": PalObjects.DateTime(PalObjects.TIME),
                                    "OwnerPlayerUId": PalObjects.Guid(OwnerPlayerUId),
                                    "OldOwnerPlayerUIds": PalObjects.ArrayProperty(
                                        "StructProperty",
                                        {
                                            "prop_name": "OldOwnerPlayerUIds",
                                            "prop_type": "StructProperty",
                                            "values": [OwnerPlayerUId],
                                            "type_name": "Guid",
                                            "id": PalObjects.EMPTY_UUID,
                                        },
                                    ),
                                    "SlotId": PalObjects.PalCharacterSlotId(
                                        SlotIndex, ContainerId
                                    ),
                                    "GotStatusPointList": PalObjects.GotStatusPointList(),
                                    "GotExStatusPointList": PalObjects.GotExStatusPointList(),
                                    "LastNickNameModifierPlayerUid": PalObjects.Guid(
                                        OwnerPlayerUId
                                    ),
                                },
                                "type": "StructProperty",
                            }
                        },
                        "unknown_bytes": [0, 0, 0, 0],
                        "group_id": group_id,
                    },
                    ".worldSaveData.CharacterSaveParameterMap.Value.RawData",
                )
            },
        }
