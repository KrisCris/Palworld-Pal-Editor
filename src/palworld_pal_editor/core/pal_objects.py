from enum import Enum
from typing import Any, Optional
from palworld_save_tools.archive import UUID

from palworld_pal_editor.utils import LOGGER, clamp


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


def get_attr_value(
    data_container: dict, attr_name: str, nested_keys: list = None
) -> Optional[Any]:
    """
    Generic method to retrieve the value of an attribute from the pal data.

    Parameters:
        attr_name (str): The name of the attribute to retrieve.
        nested_keys (list): A list of keys to navigate through nested dictionaries if necessary.

    Returns:
        Optional[Any]: The value of the attribute, or None if the attribute does not exist.
    """
    try:
        if data_container is None:
            raise TypeError("Expected dict, get None.")
        attr = data_container.get(attr_name)

        if attr is None:
            raise IndexError(f"Providing dict does not have `{attr_name}` attribute.")

        if nested_keys:
            for key in nested_keys:
                attr = attr.get(key, None)
                if attr is None:
                    raise KeyError(
                        f"trying to get attr `{attr_name}`, but nested key `{key}` not found in dict {data_container}."
                    )

        if attr and "value" in attr:
            return attr["value"]
        else:
            raise KeyError(
                f"trying to get attr `{attr_name}`, but final key `value` not found in dict {data_container}."
            )

    except Exception as e:
        # LOGGER.warning(e)
        return None


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


class PalRank(Enum):
    Rank0 = 1
    Rank1 = 2
    Rank2 = 3
    Rank3 = 4
    Rank4 = 5

    def zero_indexed(self) -> int:
        self.value - 1

    @staticmethod
    def from_value(value: int):
        if value is None:
            return None
        try:
            return PalRank(value)
        except:
            LOGGER.warning(f"{value} is not a valid PalRank")


class PalObjects:
    EMPTY_UUID = toUUID("00000000-0000-0000-0000-000000000000")

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
    def get_BaseType(container: dict) -> Optional[Any]:
        return get_nested_attr(container, ["value"])

    @staticmethod
    def set_BaseType(container: dict, value: Any):
        container["value"] = value

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
    def EnumProperty(type: str, value: str):
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
            "value": {"type": type, "value": value},
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
    def get_container_value(container: dict) -> Optional[Any]:
        case_1 = {
            "StrProperty",
            "NameProperty",
            "IntProperty",
            "Int64Property",
            "FloatProperty",
            "BoolProperty",
        }
        match container:
            case {"type": type_str, **rest} if type_str in case_1:
                return PalObjects.get_BaseType(container)
            case {"type": "StructProperty", "struct_type": "Guid", **rest}:
                return PalObjects.get_BaseType(container)
            case {"type": "EnumProperty", **rest}:
                return PalObjects.get_EnumProperty(container)
            case {"type": "ArrayProperty", **rest}:
                return PalObjects.get_ArrayProperty(container)
            case {"type": "StructProperty", "struct_type": "FixedPoint64", **rest}:
                return PalObjects.get_FixedPoint64(container)

        LOGGER.warning(f"Unhandled Pal Object Type: {container}")
        return None

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

    EPalWorkSuitabilities = [
        "EPalWorkSuitability::EmitFlame",
        "EPalWorkSuitability::Watering",
        "EPalWorkSuitability::Seeding",
        "EPalWorkSuitability::GenerateElectricity",
        "EPalWorkSuitability::Handcraft",
        "EPalWorkSuitability::Collection",
        "EPalWorkSuitability::Deforest",
        "EPalWorkSuitability::Mining",
        "EPalWorkSuitability::OilExtraction",
        "EPalWorkSuitability::ProductMedicine",
        "EPalWorkSuitability::Cool",
        "EPalWorkSuitability::Transport",
        "EPalWorkSuitability::MonsterFarm",
    ]

    @staticmethod
    def WorkSuitabilityStruct(WorkSuitability, Rank):
        return {
            "WorkSuitability": PalObjects.EnumProperty(
                "EPalWorkSuitability", WorkSuitability
            ),
            "Rank": PalObjects.IntProperty(Rank),
        }

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
                                    "Level": PalObjects.IntProperty(1),
                                    "Exp": PalObjects.IntProperty(0),
                                    "NickName": PalObjects.StrProperty("!!!NEW PAL!!!"),
                                    "EquipWaza": PalObjects.ArrayProperty(
                                        "EnumProperty", {"values": []}
                                    ),
                                    "MasteredWaza": PalObjects.ArrayProperty(
                                        "EnumProperty", {"values": []}
                                    ),
                                    "HP": PalObjects.FixedPoint64(545000),
                                    "Talent_HP": PalObjects.IntProperty(50),
                                    "Talent_Melee": PalObjects.IntProperty(50),
                                    "Talent_Shot": PalObjects.IntProperty(50),
                                    "Talent_Defense": PalObjects.IntProperty(50),
                                    "FullStomach": PalObjects.FloatProperty(150),
                                    "PassiveSkillList": PalObjects.ArrayProperty(
                                        "NameProperty", {"values": []}
                                    ),
                                    "MP": PalObjects.FixedPoint64(10000),
                                    "OwnedTime": PalObjects.DateTime(
                                        638478651098960000
                                    ),
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
                                    # "MaxHP": PalObjects.FixedPoint64(545000), # MaxHP is no longer stored in the game save.
                                    "CraftSpeed": PalObjects.IntProperty(70),
                                    "CraftSpeeds": PalObjects.ArrayProperty(
                                        "StructProperty",
                                        {
                                            "prop_name": "CraftSpeeds",
                                            "prop_type": "StructProperty",
                                            "values": [
                                                PalObjects.WorkSuitabilityStruct(
                                                    work, 0
                                                )
                                                for work in PalObjects.EPalWorkSuitabilities
                                            ],
                                            "type_name": "PalWorkSuitabilityInfo",
                                            "id": PalObjects.EMPTY_UUID,
                                        },
                                    ),
                                    # "EquipItemContainerId": {
                                    #     "struct_type": "PalContainerId",
                                    #     "struct_id": PalObjects.EMPTY_UUID,
                                    #     "id": None,
                                    #     "value": {
                                    #         "ID": {
                                    #             "struct_type": "Guid",
                                    #             "struct_id": PalObjects.EMPTY_UUID,
                                    #             "id": None,
                                    #             "value": "2ee46d97-4a5a-4e11-837c-276e4c6b9c7b",
                                    #             "type": "StructProperty",
                                    #         }
                                    #     },
                                    #     "type": "StructProperty",
                                    # },
                                    "SlotID": PalObjects.PalCharacterSlotId(
                                        SlotIndex, ContainerId
                                    ),
                                    "MaxFullStomach": PalObjects.FloatProperty(150.0),
                                    "GotStatusPointList": PalObjects.ArrayProperty(
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
                                    ),
                                    "GotExStatusPointList": PalObjects.ArrayProperty(
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
                                    ),
                                    "LastJumpedLocation": PalObjects.Vector(0, 0, 0),
                                },
                                "type": "StructProperty",
                            }
                        },
                        "unknown_bytes": (0, 0, 0, 0),
                        "group_id": group_id,
                    },
                    ".worldSaveData.CharacterSaveParameterMap.Value.RawData",
                )
            },
        }
